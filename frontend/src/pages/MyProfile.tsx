import { useEffect, useState, useRef } from 'react';

type Profile = {
  id: string; display_name: string; bio?: string; avatar_url?: string;
};
type Counts = { posts_count: number; followers_count: number; following_count: number; };
type Post = { id: string; content: string; media_url?: string; created_at: string; };

export default function MyProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [counts, setCounts] = useState<Counts | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const submittingRef = useRef(false);

  useEffect(() => {
    (async () => {
      try {
        const r1 = await fetch('/api/my/profile');
        const d1 = await r1.json();
        setProfile(d1.profile); setCounts(d1.counts);

        const r2 = await fetch('/api/my/posts');
        const d2 = await r2.json();
        setPosts(Array.isArray(d2) ? d2 : []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Telegram MainButton safe binding (prevents duplicate events)
  useEffect(() => {
    const tg = (window as any)?.Telegram?.WebApp;
    if (!tg?.MainButton) return;
    const handler = async () => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      try {
        const key = crypto.randomUUID();
        await fetch('/api/my/post', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Idempotency-Key': key },
          body: JSON.stringify({ content: 'Hello from Mini App!' })
        });
        const r2 = await fetch('/api/my/posts');
        const d2 = await r2.json();
        setPosts((prev) => mergeById(prev, d2)); // de-dupe by id
      } finally {
        submittingRef.current = false;
      }
    };
    tg.MainButton.onClick(handler);
    return () => tg.MainButton.offClick(handler); // cleanup REQUIRED
  }, []);

  if (loading) return <div>Loading…</div>;
  if (!profile) return <div>No profile yet</div>;

  return (
    <div className="my-profile">
      <header>
        <h3>{profile.display_name}</h3>
        <p>{counts?.posts_count ?? 0} Posts · {counts?.followers_count ?? 0} Followers · {counts?.following_count ?? 0} Following</p>
      </header>

      <section className="posts-grid">
        {posts.length === 0 ? (
          <div>No posts yet</div>  // no demo fallback
        ) : (
          posts.map(p => (
            <article key={p.id} className="post-card">
              {p.media_url ? <img alt="Post" src={p.media_url} /> : <div className="post-text">{p.content}</div>}
            </article>
          ))
        )}
      </section>
    </div>
  );
}

function mergeById(existing: any[], incoming: any[]) {
  const m = new Map(existing.map((x:any) => [x.id, x]));
  for (const x of incoming) m.set(x.id, x);
  return Array.from(m.values());
}