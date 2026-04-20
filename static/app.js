const API = "";

let funMessages = [
"♟ Studying your blunders...",
"🌍 Contacting countries...",
"📈 Calculating greatness...",
"🧠 Reading opening habits...",
"🔥 Measuring chess grind..."
];

let funInterval;

async function startScan(mode){

  const username =
    document.getElementById("username").value.trim();

  if(!username) return alert("Enter username");

  document.getElementById("landing").classList.add("hidden");
  document.getElementById("results").classList.add("hidden");
  document.getElementById("loading").classList.remove("hidden");

  rotateFun();

  const route =
    mode === "quick"
    ? "/analyze/"
    : "/full/";
  pollStatus(username);

  try{
    const res = await fetch(API + route + username);
    const data = await res.json();

    clearInterval(funInterval);

    showResults(data);

  }catch(err){
    console.error(err);
    alert("Something went wrong");
    resetApp();
  }
}

function rotateFun(){
  let i = 0;

  funInterval = setInterval(()=>{
    document.getElementById("funText").innerText =
      funMessages[i % funMessages.length];
    i++;
  },1500);
}

async function pollStatus(username){

  const interval = setInterval(async()=>{

    const res =
      await fetch(API + "/status/" + username);

    const data = await res.json();

    document.getElementById("statusText").innerText =
      data.status;

    document.getElementById("progressBar").style.width =
      data.progress + "%";

    if(data.progress >= 100){
      clearInterval(interval);
    }

  },1000);
}

function showResults(data){

document.getElementById("loading").classList.add("hidden");
document.getElementById("results").classList.remove("hidden");

document.getElementById("playerName").innerText =
"♟ " + data.username;

const favFormat = formatTimeControl(data.favorite_time_control);

document.getElementById("topStats").innerHTML = `

<div class="stat-card">
<h3>Games</h3>
<p>${data.games_analyzed}</p>
</div>

<div class="stat-card">
<h3>Winrate</h3>
<p class="green">${data.winrate}%</p>
</div>

<div class="stat-card">
<h3>Wins</h3>
<p class="green">${data.wins}</p>
</div>

<div class="stat-card">
<h3>Losses</h3>
<p class="red">${data.losses}</p>
</div>

<div class="stat-card">
<h3>Draws</h3>
<p>${data.draws}</p>
</div>

<div class="stat-card">
<h3>Playtime</h3>
<p>${data.estimated_playtime_hours}h</p>
</div>

<div class="stat-card">
<h3>Favorite Format</h3>
<p>${favFormat}</p>
</div>

<div class="stat-card">
<h3>Best Country</h3>
<p>${countryName(data.best_country) || "N/A"}</p>
</div>

<div class="stat-card">
<h3>Worst Country</h3>
<p>${countryName(data.worst_country) || "N/A"}</p>
</div>

<div class="stat-card">
<h3>Response</h3>
<p>${data.response_time_seconds || 0}s</p>
</div>
`;

renderCharts(data);
renderCountries(data.country_stats);
renderColorBar(data);
}

function resetApp(){

  document.getElementById("results").classList.add("hidden");
  document.getElementById("loading").classList.add("hidden");
  document.getElementById("landing").classList.remove("hidden");

  document.getElementById("progressBar").style.width = "0%";
}

function renderCharts(data){

if(typeof Chart === "undefined"){
    console.error("Chart.js not loaded");
    return;
}

if(window.resultChartObj){
    window.resultChartObj.destroy();
}

if(window.colorChartObj){
    window.colorChartObj.destroy();
}

window.resultChartObj = new Chart(
document.getElementById("resultChart"),
{
type:"doughnut",
data:{
labels:["Wins","Losses","Draws"],
datasets:[{
data:[data.wins,data.losses,data.draws]
}]
}
});

window.colorChartObj = new Chart(
document.getElementById("colorChart"),
{
type:"bar",
data:{
labels:["White","Black"],
datasets:[{
data:[data.white_games,data.black_games]
}]
}
});
}


let currentCountryStats = {};

function renderCountries(stats){

currentCountryStats = stats;

let arr = [];

for(let code in stats){

let s = stats[code];

let games = s.wins + s.losses + s.draws;

let rate = Math.round(
(s.wins / Math.max(1,games))*100
);

arr.push({
code,
name: countryName(code),
wins:s.wins,
losses:s.losses,
draws:s.draws,
games,
rate
});
}

const sort =
document.getElementById("countrySort").value;

if(sort === "wins")
arr.sort((a,b)=>b.wins-a.wins);

if(sort === "rate")
arr.sort((a,b)=>b.rate-a.rate);

if(sort === "games")
arr.sort((a,b)=>b.games-a.games);

if(sort === "losses")
arr.sort((a,b)=>b.losses-a.losses);

if(sort === "az")
arr.sort((a,b)=>a.name.localeCompare(b.name));

let query =
document.getElementById("countrySearch")
.value
.toLowerCase();

arr = arr.filter(c =>
c.name.toLowerCase().includes(query)
);

renderRival(arr);

let html = "";

arr.forEach((c,i)=>{

let medal = "";

if(i===0) medal="🥇";
if(i===1) medal="🥈";
if(i===2) medal="🥉";

html += `

<div class="country">

<strong>
<span class="rank">${medal}</span>

<img class="flag"
src="https://flagcdn.com/24x18/${c.code.toLowerCase()}.png">

${c.name}
</strong>

Wins: ${c.wins}<br>
Losses: ${c.losses}<br>
Draws: ${c.draws}<br>

<div class="small">
Games: ${c.games}<br>
Winrate: ${c.rate}%
</div>

</div>
`;
});

document.getElementById("countries").innerHTML =
html;
}


// country names
function countryName(code){

if(!code || code === "Unknown") return "Unknown";

try{
return new Intl.DisplayNames(
['en'],
{type:'region'}
).of(code.toUpperCase());
}
catch{
return code;
}
}


function formatTimeControl(tc){

if(!tc) return "Unknown";

if(tc.includes("+")){
let parts = tc.split("+");

let mins = Math.round(parseInt(parts[0]) / 60);
let inc = parts[1];

return `${mins}+${inc}`;
}

return Math.round(parseInt(tc)/60).toString();
}


function renderColorBar(data){

let total = data.white_games + data.black_games;

let whitePct =
Math.round((data.white_games / total) * 100);

let blackPct = 100 - whitePct;

const html = `

<div class="section">

<h2>⚔ White vs Black</h2>

<div class="colorWrap">

<div class="whiteSide"
style="width:${whitePct}%">
♔ ${whitePct}%
</div>

<div class="blackSide"
style="width:${blackPct}%">
${blackPct}% ♚
</div>

</div>

</div>
`;

document
.getElementById("countries")
.insertAdjacentHTML("beforebegin", html);
}
alert
function filterCountries(){
renderCountries(currentCountryStats);
}


function renderRival(arr){

if(arr.length === 0) return;

let rival = arr.reduce((a,b)=>
a.games > b.games ? a : b
);

document.getElementById("rivalBox").innerHTML =
`🔥 Main Rival:
${rival.name}
(${rival.games} games)`;
}