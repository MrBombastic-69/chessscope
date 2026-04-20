from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from collections import Counter
import httpx
import json
import asyncio
import re
import time
import os



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "ChessStatsApp/1.0"
}


status_store = {}
country_cache = {}


def update_status(username, status, progress, eta):
    status_store[username] = {
        "username": username,
        "status": status,
        "progress": progress,
        "eta_seconds": eta
    }


# 🔹 Home
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

# 🔹 Return cached stats
@app.get("/stats/{username}")
def get_stats(username: str):
    file = f"data/{username}.json"

    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)

    return {"error": "No data found"}


@app.get("/status/{username}")
def get_status(username: str):

    username = username.lower().strip()

    return status_store.get(
        username,
        {
            "username": username,
            "status": "Not Started",
            "progress": 0,
            "eta_seconds": None
        }
    )


@app.get("/analyze/{username}")
async def analyze(username: str):

    update_status(username, "Fetching archives...", 5, 8)
    
    start = time.time()
    username = username.lower().strip()

    status_store[username] = "Fetching archives..."

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=20.0
    ) as client:

        archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

        res = await client.get(
            archives_url,
            follow_redirects=True
        )

        if res.status_code != 200:
            status_store[username] = "Failed"
            return {"error": "User not found"}

        archives = res.json().get("archives", [])

        if not archives:
            status_store[username] = "Failed"
            return {"error": "No games found"}

        archives.reverse()

        games = []

        update_status(username, "Loading recent games...", 25, 6)

        for archive in archives:

            if len(games) >= 100:
                break

            r = await client.get(
                archive,
                follow_redirects=True
            )

            if r.status_code != 200:
                continue

            monthly = r.json().get("games", [])
            monthly.reverse()

            for g in monthly:

                if g["time_class"] in [
                    "rapid",
                    "blitz",
                    "bullet"
                ]:
                    games.append(g)

                if len(games) >= 100:
                    break

        update_status(username, "Mapping countries...", 55, 4)

        # Unique opponents
        opponents = set()

        for g in games:
            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()

            opp = black if white == username else white
            opponents.add(opp)

        semaphore = asyncio.Semaphore(12)

        async def get_country(user):

            if user in country_cache:
                return user, country_cache[user]

            async with semaphore:
                try:
                    rr = await client.get(
                        f"https://api.chess.com/pub/player/{user}",
                        follow_redirects=True
                    )

                    if rr.status_code == 200:
                        data = rr.json()
                        cu = data.get("country", "")
                        code = cu.split("/")[-1] if cu else "Unknown"
                    else:
                        code = "Unknown"

                except:
                    code = "Unknown"

            country_cache[user] = code
            return user, code

        results = await asyncio.gather(
            *[get_country(u) for u in opponents]
        )

        country_map = dict(results)

        update_status(username, "Generating insights...", 82, 2)

        # Stats
        wins = losses = draws = 0
        country_stats = {}
        white_games = black_games = 0
        time_controls = Counter()

        for g in games:

            tc = g.get("time_control", "Unknown")
            time_controls[tc] += 1

            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()

            if white == username:
                result = g["white"]["result"]
                opp = black
                white_games += 1
            else:
                result = g["black"]["result"]
                opp = white
                black_games += 1

            if result == "win":
                wins += 1
                rk = "wins"

            elif result in [
                "agreed",
                "stalemate",
                "repetition",
                "insufficient",
                "50move"
            ]:
                draws += 1
                rk = "draws"

            else:
                losses += 1
                rk = "losses"

            country = country_map.get(opp, "Unknown")

            if country not in country_stats:
                country_stats[country] = {
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }

            country_stats[country][rk] += 1

        total = len(games)

        update_status(username, "Done", 100, 0)
        
        best_country = None
        worst_country = None

        if country_stats:
            best_country = max(
                country_stats.items(),
                key=lambda x: x[1]["wins"] - x[1]["losses"]
            )[0]

            worst_country = min(
                country_stats.items(),
                key=lambda x: x[1]["wins"] - x[1]["losses"]
            )[0]
        
        return {
            "mode": "quick",
            "response_time_seconds":
                round(time.time() - start, 2),

            "username": username,
            "games_analyzed": total,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "estimated_playtime_hours": 0,
            "best_country": best_country,
            "worst_country": worst_country,

            "winrate":
                round((wins / total) * 100, 1)
                if total else 0,

            "favorite_time_control":
                time_controls.most_common(1)[0][0]
                if time_controls else None,

            "white_games": white_games,
            "black_games": black_games,

            "country_stats": country_stats
        }

@app.get("/full/{username}")
async def analyze(username: str):
    start = time.time()

    username = username.lower().strip()

    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=25.0
    ) as client:

        # 🔥 Step 1: Get archives
        res = await client.get(
            archives_url,
            follow_redirects=True
        )

        if res.status_code != 200:
            return {"error": "User not found"}

        archives = res.json().get("archives", [])

        if not archives:
            return {"error": "No archives"}

        archives.reverse()   # newest first

        # =====================================================
        # 🔥 STEP 2: FETCH ALL MONTH ARCHIVES CONCURRENTLY
        # =====================================================

        semaphore = asyncio.Semaphore(12)

        async def fetch_archive(url):
            async with semaphore:
                try:
                    r = await client.get(
                        url,
                        follow_redirects=True
                    )

                    if r.status_code == 200:
                        return r.json().get("games", [])
                except:
                    pass

                return []

        archive_results = await asyncio.gather(
            *[fetch_archive(a) for a in archives]
        )

        # =====================================================
        # 🔥 STEP 3: COLLECT ALL SUPPORTED GAMES
        # =====================================================

        games = []

        for monthly_games in archive_results:

            monthly_games.reverse()

            for g in monthly_games:

                if g["time_class"] in [
                    "rapid",
                    "blitz",
                    "bullet"
                ]:
                    games.append(g)

        # =====================================================
        # 🔥 STEP 4: UNIQUE OPPONENTS
        # =====================================================

        opponents = set()

        for g in games:
            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()

            opp = black if white == username else white
            opponents.add(opp)

        # =====================================================
        # 🔥 STEP 5: FETCH COUNTRIES CONCURRENTLY + CACHE
        # =====================================================

        async def get_country(user):

            if user in country_cache:
                return user, country_cache[user]

            async with semaphore:
                try:
                    r = await client.get(
                        f"https://api.chess.com/pub/player/{user}",
                        follow_redirects=True
                    )

                    if r.status_code == 200:
                        data = r.json()
                        c_url = data.get("country", "")
                        code = (
                            c_url.split("/")[-1]
                            if c_url else "Unknown"
                        )
                    else:
                        code = "Unknown"

                except:
                    code = "Unknown"

            country_cache[user] = code
            return user, code

        country_results = await asyncio.gather(
            *[get_country(u) for u in opponents]
        )

        country_map = dict(country_results)

        # =====================================================
        # 🔥 STEP 6: BETTER PLAYTIME MODEL
        # =====================================================

        def estimate_game_time(game):

            tc = game.get("time_control", "600")
            pgn = game.get("pgn", "")

            full_moves = len(
                re.findall(r'\d+\.', pgn)
            )

            if full_moves == 0:
                full_moves = 20

            base = 600
            inc = 0

            try:
                if "+" in tc:
                    base, inc = tc.split("+")
                    base = int(base)
                    inc = int(inc)

                elif tc.isdigit():
                    base = int(tc)

                else:
                    base = 600

            except:
                base = 600
                inc = 0

            # realistic pace
            if base <= 120:
                sec_per_move = 2
            elif base <= 300:
                sec_per_move = 3.8
            elif base <= 600:
                sec_per_move = 6
            elif base <= 900:
                sec_per_move = 8
            else:
                sec_per_move = 11

            sec_per_move += min(inc, 10) * 0.25

            duration = full_moves * sec_per_move

            # early resignation likely
            if full_moves < 15:
                duration *= 0.65

            # cap
            max_duration = base * 1.45

            return min(duration, max_duration)

        # =====================================================
        # 🔥 STEP 7: PROCESS STATS
        # =====================================================

        wins = losses = draws = 0
        white_games = black_games = 0
        playtime = 0

        time_controls = Counter()
        country_stats = {}

        for g in games:

            tc = g.get("time_control", "Unknown")
            time_controls[tc] += 1

            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()

            if white == username:
                my_result = g["white"]["result"]
                opp = black
                white_games += 1
            else:
                my_result = g["black"]["result"]
                opp = white
                black_games += 1

            # result logic
            if my_result == "win":
                wins += 1
                rk = "wins"

            elif my_result in [
                "agreed",
                "stalemate",
                "repetition",
                "insufficient",
                "50move"
            ]:
                draws += 1
                rk = "draws"

            else:
                losses += 1
                rk = "losses"

            # playtime
            playtime += estimate_game_time(g)

            # country stats
            country = country_map.get(
                opp,
                "Unknown"
            )

            if country not in country_stats:
                country_stats[country] = {
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }

            country_stats[country][rk] += 1

        # =====================================================
        # 🔥 STEP 8: INSIGHTS
        # =====================================================

        total = len(games)

        best_country = None
        worst_country = None

        if country_stats:

            best_country = max(
                country_stats.items(),
                key=lambda x:
                x[1]["wins"] - x[1]["losses"]
            )[0]

            worst_country = min(
                country_stats.items(),
                key=lambda x:
                x[1]["wins"] - x[1]["losses"]
            )[0]

        elapsed = round(
            time.time() - start,
            2
        )

        return {
            "response_time_seconds": elapsed,
            "username": username,
            "games_analyzed": total,

            "wins": wins,
            "losses": losses,
            "draws": draws,

            "winrate":
                round((wins / total) * 100, 1)
                if total else 0,

            "estimated_playtime_hours":
                round(playtime / 3600, 2),

            "favorite_time_control":
                time_controls.most_common(1)[0][0]
                if time_controls else None,

            "white_games": white_games,
            "black_games": black_games,

            "best_country": best_country,
            "worst_country": worst_country,

            "country_stats": country_stats
        }