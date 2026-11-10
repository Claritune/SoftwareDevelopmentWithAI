import { api, getToken, setToken, poll } from "/static/common.js";

const [, , gameId, , sessionId] = location.pathname.split("/");
const el = (id) => document.getElementById(id);
let token = getToken(sessionId);
let view, lastVersion = null;

el("lobby").href = `/games/${gameId}`;
el("title").textContent = `Game ${sessionId}`;

async function ensureSeat() {
  if (token) return;
  const s = await api(`/api/sessions/${sessionId}/state`);
  if (s.lifecycle !== "waiting") return;               // full: watch without a seat
  try {
    const a = await api(`/api/sessions/${sessionId}/join`, { method: "POST" });
    token = a.token; setToken(sessionId, token);
  } catch (e) { if (e.status !== 409) throw e; }       // lost the race: full
}

function statusText(s) {
  const scores = Object.entries(s.status.scores).map(([k, v]) => `${k} ${v}`).join(" · ");
  if (s.your_seat === null) return `Session full, watching only · ${scores}`;
  if (s.lifecycle === "waiting") return `You are ${s.your_seat}. Waiting for opponent…`;
  const turn = s.status.to_move === s.your_seat ? "Your turn" : "Opponent's turn";
  return `You are ${s.your_seat} · ${turn} · ${scores}`;
}

function show(s) {
  if (s.version === lastVersion) return;
  lastVersion = s.version;
  view.render(el("board"), s.public_state, s.legal_moves, null);   // Phase 3 passes onMove
  el("status").textContent = statusText(s);
}

async function main() {
  try {
    view = await import(`/games/${gameId}/static/view.js`);
  } catch {
    el("error").textContent = `Could not load the view for "${gameId}".`; return;
  }
  try {
    await ensureSeat();
  } catch (e) {
    el("error").textContent = e.status === 404 ? "Session not found." : e.message; return;
  }
  poll(async () => {
    try {
      show(await api(`/api/sessions/${sessionId}/state`, { token }));
      el("error").textContent = "";
    } catch (e) {
      el("error").textContent = e.status === 404 ? "Session not found." : e.message;
    }
  }, 1000);
}
main();
