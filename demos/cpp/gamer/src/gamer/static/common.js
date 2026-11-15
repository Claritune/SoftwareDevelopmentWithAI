export async function api(path, { method = "GET", body, token } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["X-Player-Token"] = token;
  const res = await fetch(path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(data?.detail ?? res.statusText);
    err.status = res.status;
    throw err;
  }
  return data;
}

const tokenKey = (sid) => `gamer.token.${sid}`;
export const getToken = (sid) => sessionStorage.getItem(tokenKey(sid));   // per tab
export const setToken = (sid, token) => sessionStorage.setItem(tokenKey(sid), token);

// Runs fn now, then every `ms` after each run finishes (no overlapping requests).
export function poll(fn, ms) {
  let stopped = false, timer;
  const tick = async () => {
    try { await fn(); } catch (e) { console.error(e); }
    if (!stopped) timer = setTimeout(tick, ms);
  };
  tick();
  return () => { stopped = true; clearTimeout(timer); };
}
