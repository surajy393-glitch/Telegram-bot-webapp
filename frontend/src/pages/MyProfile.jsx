import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function MyProfile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [editingBio, setEditingBio] = useState(false);
  const [newBio, setNewBio] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      
      // Get user from localStorage first
      const localUser = localStorage.getItem('luvhive_user');
      let currentUser = null;
      
      if (localUser) {
        try {
          currentUser = JSON.parse(localUser);
          console.log('✅ User from localStorage:', currentUser.username);
        } catch (e) {
          console.error('Failed to parse localStorage user:', e);
        }
      }
      
      // If no user in localStorage, try backend with dev user
      if (!currentUser) {
        console.log('⚠️ No user in localStorage, using dev mode');
        const userRes = await fetch(`${backendUrl}/api/me`, {
          headers: { 'X-Dev-User': '123456789' }
        });
        
        if (userRes.ok) {
          const data = await userRes.json();
          currentUser = data.user || data;
        }
      }
      
      if (currentUser) {
        setUser(currentUser);
        setNewBio(currentUser.bio || "");
        
        // Load posts from backend using username
        try {
          const postsRes = await fetch(`${backendUrl}/api/profile/posts`, {
            headers: { 
              'X-Dev-User': '123456789',
              'X-Username': currentUser.username || 'luvsociety'
            }
          });
          
          if (postsRes.ok) {
            const postsData = await postsRes.json();
            console.log('✅ Posts from backend:', postsData.length || 0);
            setPosts(postsData || []);
          } else {
            console.log('⚠️ Failed to load posts from backend');
            // Fallback to localStorage posts
            const localPosts = localStorage.getItem(`luvhive_posts_${currentUser.username}`);
            if (localPosts) {
              setPosts(JSON.parse(localPosts));
            }
          }
        } catch (postError) {
          console.error('Error loading posts:', postError);
        }
      }
      
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePicUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/upload-photo`, {
        method: 'POST',
        headers: { 'X-Dev-User': '647778438' },
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setUser({...user, avatar_url: data.photo_url});
        alert('✅ Profile picture updated!');
      } else {
        alert('❌ Upload failed');
      }
    } catch (error) {
      alert('❌ Upload error');
    } finally {
      setUploading(false);
    }
  };

  const handleBioSave = async () => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/onboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Dev-User': '647778438'
        },
        body: JSON.stringify({
          ...user,
          bio: newBio
        })
      });
      
      if (res.ok) {
        setUser({...user, bio: newBio});
        setEditingBio(false);
        alert('✅ Bio updated!');
      }
    } catch (error) {
      alert('❌ Failed to update bio');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center">
        <div className="text-white text-xl font-semibold">Loading profile...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 text-center">
          <div className="text-6xl mb-4">😕</div>
          <h2 className="text-2xl font-bold text-white mb-2">Profile Not Found</h2>
          <p className="text-white/80 mb-6">Unable to load user data</p>
          <button
            onClick={() => navigate('/feed')}
            className="bg-white text-purple-600 px-6 py-3 rounded-full font-semibold"
          >
            Go to Feed
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <button 
            onClick={() => navigate('/feed')}
            className="text-white text-2xl hover:opacity-80 transition"
          >
            ← Back
          </button>
          <h1 className="text-white text-xl font-bold">My Profile</h1>
          <button className="text-white text-2xl hover:opacity-80 transition">⋮</button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Profile Card */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 border border-white/20">
          <div className="flex flex-col items-center text-center mb-6">
            {/* Avatar with Upload */}
            <div className="relative mb-4">
              <div className="w-28 h-28 rounded-full bg-gradient-to-br from-yellow-400 to-pink-500 p-1">
                <div className="w-full h-full rounded-full overflow-hidden bg-gray-800">
                  {user.avatar_url ? (
                    <img 
                      src={user.avatar_url} 
                      alt="Profile" 
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-4xl text-white">
                      {user.display_name?.[0] || '👤'}
                    </div>
                  )}
                </div>
              </div>
              <label className="absolute bottom-0 right-0 w-10 h-10 bg-green-500 rounded-full flex items-center justify-center cursor-pointer hover:bg-green-600 transition border-4 border-white shadow-lg">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePicUpload}
                  disabled={uploading}
                  className="hidden"
                />
                <span className="text-white text-lg">{uploading ? '⏳' : '📷'}</span>
              </label>
            </div>

            {/* User Info */}
            <h2 className="text-3xl font-bold text-white mb-1">
              {user.display_name || 'User'}
            </h2>
            <p className="text-white/70 text-lg mb-4">
              @{user.username || 'username'}
            </p>

            {/* Bio */}
            {editingBio ? (
              <div className="w-full space-y-3">
                <textarea
                  value={newBio}
                  onChange={(e) => setNewBio(e.target.value)}
                  className="w-full bg-white/10 text-white placeholder-white/50 border border-white/30 rounded-xl px-4 py-3 focus:outline-none focus:border-white/50"
                  rows="3"
                  placeholder="Tell us about yourself..."
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleBioSave}
                    className="flex-1 bg-white text-purple-600 py-2 rounded-full font-semibold"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingBio(false)}
                    className="flex-1 bg-white/20 text-white py-2 rounded-full font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="w-full">
                <p className="text-white/90 mb-2">
                  {user.bio || "No bio yet - click edit to add one!"}
                </p>
                <button
                  onClick={() => setEditingBio(true)}
                  className="text-yellow-300 hover:text-yellow-200 font-semibold text-sm"
                >
                  ✏️ Edit Bio
                </button>
              </div>
            )}
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white/10 rounded-xl p-4 text-center backdrop-blur">
              <div className="text-3xl font-bold text-white mb-1">{posts.length}</div>
              <div className="text-white/70 text-sm">Posts</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 text-center backdrop-blur">
              <div className="text-3xl font-bold text-white mb-1">{user.followers_count || 0}</div>
              <div className="text-white/70 text-sm">Followers</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 text-center backdrop-blur">
              <div className="text-3xl font-bold text-white mb-1">{user.following_count || 0}</div>
              <div className="text-white/70 text-sm">Following</div>
            </div>
          </div>

          {/* Quick Info */}
          <div className="space-y-2 text-sm">
            {user.age && (
              <div className="flex items-center text-white/80">
                <span className="mr-2">🎂</span>
                <span>{user.age} years old</span>
              </div>
            )}
            <div className="flex items-center text-white/80">
              <span className="mr-2">📅</span>
              <span>Joined {new Date().toLocaleDateString('en-US', {month: 'long', year: 'numeric'})}</span>
            </div>
            <div className="flex items-center text-white/80">
              <span className="mr-2">✨</span>
              <span>Active Member</span>
            </div>
          </div>
        </div>

        {/* Posts Section */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 border border-white/20">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-white">My Posts</h3>
            <span className="text-white/70 text-lg">{posts.length} total</span>
          </div>

          {posts.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📝</div>
              <h4 className="text-xl font-semibold text-white mb-2">No Posts Yet</h4>
              <p className="text-white/70 mb-6">Start sharing your thoughts with the world!</p>
              <button
                onClick={() => navigate('/feed')}
                className="bg-white text-purple-600 px-6 py-3 rounded-full font-semibold hover:shadow-lg transition"
              >
                Create First Post
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <div 
                  key={post.id} 
                  className="bg-white/5 rounded-2xl p-4 border border-white/10 hover:bg-white/10 transition"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-pink-500 flex-shrink-0 overflow-hidden">
                      {user.avatar_url ? (
                        <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xl text-white">
                          {user.display_name?.[0] || '👤'}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-white">{user.display_name}</span>
                        <span className="text-white/50 text-xs">
                          {post.created_at ? new Date(post.created_at).toLocaleDateString() : 'Just now'}
                        </span>
                      </div>
                      
                      {post.text && (
                        <p className="text-white/90 mb-3 leading-relaxed">{post.text}</p>
                      )}
                      
                      {post.photo_url && (
                        <div className="rounded-xl overflow-hidden mb-3">
                          <img
                            src={post.photo_url}
                            alt="Post"
                            className="w-full h-auto"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        </div>
                      )}
                      
                      {post.video_url && (
                        <div className="rounded-xl overflow-hidden mb-3">
                          <video
                            src={post.video_url}
                            controls
                            className="w-full h-auto"
                          />
                        </div>
                      )}
                      
                      <div className="flex items-center gap-6 text-white/60 text-sm">
                        <span className="flex items-center gap-1">
                          <span>❤️</span>
                          <span>{post.likes_count || 0}</span>
                        </span>
                        <span className="flex items-center gap-1">
                          <span>💬</span>
                          <span>{post.comments_count || 0}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
