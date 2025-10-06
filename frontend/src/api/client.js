// frontend/src/api/client.js
const API_BASE = "";

function headers() {
  const h = { "Content-Type": "application/json" };
  // Telegram WebApp initData pass karo (frontend se)
  const initData =
    window?.Telegram?.WebApp?.initData || sessionStorage.getItem("initData");
  if (initData) h["X-Telegram-Init-Data"] = initData;
  // Dev: use X-Dev-User when ALLOW_INSECURE_TRIAL=1 (optional)
  const devUser = sessionStorage.getItem("X-Dev-User");
  if (devUser) h["X-Dev-User"] = devUser;
  return h;
}

export async function getMe() {
  const r = await fetch(`${API_BASE}/api/me`, { headers: headers() });
  return r.json();
}

export async function getMyPosts() {
  const r = await fetch(`${API_BASE}/api/my/posts`, { headers: headers() });
  return r.json();
}

export async function getMySaved() {
  const r = await fetch(`${API_BASE}/api/my/saved`, { headers: headers() });
  return r.json();
}
