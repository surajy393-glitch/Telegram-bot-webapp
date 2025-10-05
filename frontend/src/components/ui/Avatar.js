// src/components/common/Avatar.jsx
export default function Avatar({ user, size = 40 }) {
  const v = user?.avatarVersion ?? 0;
  const base = user?.avatarUrl || user?.profilePic || '/avatar-fallback.png';
  const src = `${base}${base.includes('?') ? '&' : '?'}v=${v}`;
  return <img src={src} width={size} height={size} alt="avatar" style={{ borderRadius: '50%' }} />;
}