import * as api from "./api.js";

const POLL_MS = 1000;
const view = document.getElementById("view");
const seats = new Map();
let routeToken = 0;
let stopPolling = () => {};

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith("on")) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  node.append(...children);
  return node;
}

function parseRoute() {
  const [gameId, code] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { gameId, code };
}

async function route() {
  stopPolling();
  stopPolling = () => {};
  const token = ++routeToken;
  const { gameId, code } = parseRoute();
  if (!gameId) return showDirectory(token);
  if (!code) return showLobby(gameId, token);
  return showGame(gameId, code.toUpperCase(), token);
}

function poll(fn) {
  let stopped = false;
  let timer;
  const tick = async () => {
    let keepGoing = true;
    try { keepGoing = await fn(); } catch { /* transient error: retry next tick */ }
    if (!stopped && keepGoing !== false) timer = setTimeout(tick, POLL_MS);
  };
  tick();
  return () => { stopped = true; clearTimeout(timer); };
}

function nameForm(label, onSubmit) {
  const input = el("input", { name: "name", maxlength: "32", required: "", placeholder: "Your name" });
  const error = el("p", { class: "error" });
  const form = el("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      error.textContent = "";
      const name = input.value.trim();
      if (!name) {
        error.textContent = "Enter your name";
        return;
      }
      try {
        await onSubmit(name);
      } catch (err) {
        error.textContent = err.message;
      }
    },
  }, input, el("button", { type: "submit" }, label), error);
  return form;
}

function label(state, seat) {
  return `${state.seat_labels[seat]} (${state.players[seat]?.name ?? "?"})`;
}

function scores(state) {
  return state.scores.map((s, i) => `${state.seat_labels[i]} ${s}`).join(" – ");
}

function describe(state, mySeat) {
  if (state.status === "waiting") return "Waiting for opponent…";
  if (state.status === "finished") {
    const result = state.winner === null ? "Draw" : `${label(state, state.winner)} wins`;
    return `${result} · ${scores(state)}`;
  }
  const current = state.current_player;
  let text = `${label(state, current)} to move${current === mySeat ? " (you)" : ""}`;
  if (state.last_event) text += ` · ${state.last_event}`;
  return `${text} · ${scores(state)}`;
}

async function showDirectory(token) {
  view.replaceChildren(el("h1", {}, "Games"), el("p", {}, "Loading…"));
  try {
    const games = await api.listGames();
    if (token !== routeToken) return;
    view.replaceChildren(
      el("h1", {}, "Games"),
      el("ul", { id: "games" }, ...games.map((g) => el("li", {}, el("a", { href: `#/${g.id}` }, g.name)))),
    );
  } catch (e) {
    view.replaceChildren(el("p", { class: "error" }, e.message));
  }
}

function showLobby(gameId, token) {
  view.replaceChildren(
    el("h1", {}, gameId),
    nameForm("Create session", async (name) => {
      const joined = await api.createSession(gameId, name);
      seats.set(joined.code, { playerId: joined.player_id, seat: joined.seat });
      if (token === routeToken) location.hash = `#/${gameId}/${joined.code}`;
    }),
  );
}

async function showGame(gameId, code, token) {
  if (!seats.has(code)) {
    view.replaceChildren(el("h1", {}, `Join ${code}`), nameForm("Join", async (name) => {
      try {
        const joined = await api.joinSession(code, name);
        seats.set(code, { playerId: joined.player_id, seat: joined.seat });
        if (token === routeToken) showGame(gameId, code, token);
      } catch (e) {
        view.replaceChildren(el("p", { class: "error" },
          e.status === 409 ? "Session full" : e.status === 404 ? "Session not found" : e.message));
      }
    }));
    return;
  }
  const mine = seats.get(code);
  const renderer = await import(`/games/${gameId}.js`);
  if (token !== routeToken) return;
  const status = el("p", { id: "status" });
  const board = el("div", { id: "board" });
  const error = el("p", { class: "error" });
  const link = `${location.origin}/#/${gameId}/${code}`;
  view.replaceChildren(el("h1", {}, `Session ${code}`),
    el("p", {}, "Share: ", el("a", { href: link }, link)), status, board, error);

  let lastVersion = -1;
  const onMove = () => {};
  const show = (state) => {
    if (state.version === lastVersion) return;
    lastVersion = state.version;
    status.textContent = describe(state, mine.seat);
    renderer.render(board, state, { mySeat: mine.seat, onMove });
  };
  stopPolling = poll(async () => {
    const state = await api.getSession(code);
    if (token !== routeToken) return false;
    show(state);
    return state.status !== "finished";
  });
}

window.addEventListener("hashchange", route);
route();
