# ChessScope ♟

Analyze Chess.com profiles with deep statistics, country matchups, winrates, playtime estimates, and interactive dashboards.

## Features

- Quick Scan (last 100 games)
- Deep Scan (full history)
- Live progress system
- Country leaderboard with flags
- Charts & visual analytics
- FastAPI backend
- Premium frontend UI

## Tech Stack

- Python
- FastAPI
- HTML/CSS/JavaScript
- Chess.com Public API

## Run Locally

### Backend

uvicorn main:app --reload

### Frontend

python -m http.server 5500

Then open:
http://localhost:5500

## Future Plans

- PostgreSQL database
- User accounts
- Global rankings
- World map heatmaps
- Premium reports