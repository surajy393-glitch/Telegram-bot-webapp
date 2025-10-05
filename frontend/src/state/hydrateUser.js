// src/state/hydrateUser.js
export function hydrateUser() {
  try {
    const legacy = JSON.parse(localStorage.getItem('luvhive_user') || 'null')
               || JSON.parse(localStorage.getItem('user') || 'null');
    const current = JSON.parse(localStorage.getItem('lh_user') || 'null');
    const user = current || legacy;
    if (user) localStorage.setItem('lh_user', JSON.stringify(user));
  } catch {}
}