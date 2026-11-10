import { api, setToken, poll } from "/static/common.js";

const gameId = location.pathname.split("/")[2];
const el = (id) => document.getElementById(id);

async function loadTitle() {
  try {
    const games = await api("/api/games");
    const game = games.find((g) => g.id === gameId);
    if (game) {
      el("title").textContent = game.name;
      document.title = `Gamer · ${game.name}`;
    }
  } catch (e) {
    el("error").textContent = e.message;
  }
}

el("create").addEventListener("click", async () => {
  try {
    const a = await api(`/api/games/${gameId}/sessions`, { method: "POST" });
    setToken(a.session_id, a.token);
    location.href = `/games/${gameId}/sessions/${a.session_id}`;
  } catch (e) {
    el("error").textContent = e.message;
  }
});

function renderSessions(sessions) {
  const list = el("sessions");
  if (sessions.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No open games";
    list.replaceChildren(li);
    return;
  }
  list.replaceChildren(...sessions.map(({ session_id: sid }) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `/games/${gameId}/sessions/${sid}`;
    a.textContent = `Join game ${sid}`;
    li.append(a);
    return li;
  }));
}

loadTitle();
poll(async () => {
  try {
    renderSessions(await api(`/api/games/${gameId}/sessions`));
    el("error").textContent = "";
  } catch (e) {
    el("error").textContent = e.message;
  }
}, 2000);
