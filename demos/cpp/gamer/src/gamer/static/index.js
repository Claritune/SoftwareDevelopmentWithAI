import { api } from "/static/common.js";

const list = document.getElementById("games");
const error = document.getElementById("error");

try {
  const games = await api("/api/games");
  for (const game of games) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `/games/${encodeURIComponent(game.id)}`;
    a.textContent = game.name;
    li.append(a);
    list.append(li);
  }
} catch (err) {
  error.textContent = `Could not load games: ${err.message}`;
  error.hidden = false;
}
