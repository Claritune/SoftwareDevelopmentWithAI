import * as api from "./api.js";

const view = document.getElementById("view");
let routeToken = 0;

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
  const token = ++routeToken;
  const { gameId, code } = parseRoute();
  if (!gameId) return showDirectory(token);
  view.replaceChildren(el("p", {}, code ? `Session ${code}` : `Lobby for ${gameId}`));
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

window.addEventListener("hashchange", route);
route();
