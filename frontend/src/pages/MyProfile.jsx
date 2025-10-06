// frontend/src/pages/MyProfile.jsx
import React, { useEffect, useState } from "react";
import { getMe, getMyPosts, getMySaved } from "../api/client";

function Count({label, value}) {
  return (
    <div style={{textAlign:"center"}}>
      <div style={{fontWeight:700}}>{value ?? 0}</div>
      <div style={{fontSize:12, opacity:.7}}>{label}</div>
    </div>
  );
}

function PostCard({p}) {
  const isVideo = !!p.video_url;
  const src = p.photo_url || p.video_url;
  return (
    <div style={{borderRadius:12, overflow:"hidden", background:"#111", aspectRatio:"1/1"}}>
      {isVideo ? (
        <video src={src} style={{width:"100%", height:"100%", objectFit:"cover"}} controls />
      ) : src ? (
        <img src={src} alt="" style={{width:"100%", height:"100%", objectFit:"cover"}} />
      ) : (
        <div style={{padding:12, fontSize:13}}>{p.text}</div>
      )}
    </div>
  );
}

export default function MyProfile() {
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("posts"); // posts|saved|followers|following
  const [posts, setPosts] = useState([]);
  const [saved, setSaved] = useState([]);

  useEffect(() => {
    getMe().then(res => setUser(res.user));
    getMyPosts().then(res => setPosts(res.posts || []));
  }, []);

  useEffect(() => {
    if (tab === "saved" && saved.length === 0) {
      getMySaved().then(res => setSaved(res.posts || []));
    }
  }, [tab, saved.length]);

  if (!user) return <div style={{padding:16}}>Loading…</div>;

  const counts = {
    posts: posts.length,
    followers: user.followers_count ?? 0,
    following: user.following_count ?? 0,
  };

  return (
    <div style={{maxWidth:680, margin:"0 auto", padding:"16px"}}>
      {/* Header */}
      <div style={{display:"flex", gap:16, alignItems:"center"}}>
        <div style={{width:84, height:84, borderRadius:"50%", overflow:"hidden", background:"#222"}}>
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" style={{width:"100%", height:"100%", objectFit:"cover"}} />
          ) : null}
        </div>
        <div style={{flex:1}}>
          <div style={{fontWeight:700, fontSize:18}}>{user.display_name || user.username}</div>
          <div style={{opacity:.7, fontSize:12}}>@{user.username}</div>
          <div style={{marginTop:10, display:"grid", gridTemplateColumns:"repeat(3,1fr)"}}>
            <Count label="Posts" value={counts.posts} />
            <Count label="Followers" value={counts.followers} />
            <Count label="Following" value={counts.following} />
          </div>
        </div>
      </div>

      {/* Buttons */}
      <div style={{display:"flex", gap:8, marginTop:12}}>
        <button style={btn} onClick={()=>alert("Edit Profile screen (todo)")}>Edit Profile</button>
        <button style={btnOutline} onClick={()=>alert("Settings screen (todo)")}>Settings</button>
      </div>

      {/* Story highlights row (dummy for now; fill from API when ready) */}
      <div style={{display:"flex", gap:12, margin:"16px 0", overflowX:"auto"}}>
        {["New","Travel","Food","Friends","Work"].map((t,i)=>(
          <div key={i} style={{textAlign:"center"}}>
            <div style={{width:58, height:58, borderRadius:"50%", background:"#1f1f1f", margin:"0 auto"}}/>
            <div style={{fontSize:11, marginTop:6, opacity:.8}}>{t}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{display:"flex", gap:16, fontSize:13, borderBottom:"1px solid #222"}}>
        {["posts","saved","followers","following"].map(k=>(
          <div key={k}
               onClick={()=>setTab(k)}
               style={{padding:"8px 0", cursor:"pointer", borderBottom: tab===k ? "2px solid #fff":"2px solid transparent"}}>
            {k[0].toUpperCase()+k.slice(1)}
          </div>
        ))}
      </div>

      {/* Content */}
      {tab === "posts" && (
        <div style={grid}>
          {posts.map(p => <PostCard key={p.id} p={p} />)}
          {posts.length === 0 && <div style={{padding:24, opacity:.8}}>No posts yet.</div>}
        </div>
      )}
      {tab === "saved" && (
        <div style={grid}>
          {saved.map(p => <PostCard key={p.id} p={p} />)}
          {saved.length === 0 && <div style={{padding:24, opacity:.8}}>Nothing saved yet.</div>}
        </div>
      )}
      {tab === "followers" && <div style={{padding:16}}>Followers list (add API later)</div>}
      {tab === "following" && <div style={{padding:16}}>Following list (add API later)</div>}
    </div>
  );
}

const btn = {
  flex:1, padding:"10px 12px", borderRadius:10, border:"none", background:"#fff", color:"#000", fontWeight:600
};
const btnOutline = {
  ...btn, background:"transparent", color:"#fff", border:"1px solid #444"
};
const grid = {
  marginTop:12,
  display:"grid",
  gridTemplateColumns:"repeat(3, 1fr)",
  gap:8
};
