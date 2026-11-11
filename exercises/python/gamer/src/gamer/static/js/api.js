export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const env = (type, payload) => ({ v: 1, type, payload });

async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, data?.payload?.code ?? "http_error",
                       data?.payload?.message ?? res.statusText);
  }
  return data.payload;
}

export const listGames = () => request("GET", "/api/games");
export const listSessions = (gameId) => request("GET", `/api/games/${gameId}/sessions`);
export const createSession = (gameId, name) =>
  request("POST", `/api/games/${gameId}/sessions`, env("create", { name }));
export const joinSession = (code, name) =>
  request("POST", `/api/sessions/${code}/join`, env("join", { name }));
export const getSession = (code) => request("GET", `/api/sessions/${code}`);
export const makeMove = (code, playerId, move) =>
  request("POST", `/api/sessions/${code}/moves`, env("move", { player_id: playerId, move }));
