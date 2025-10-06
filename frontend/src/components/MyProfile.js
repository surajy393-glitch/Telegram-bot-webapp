import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const MyProfile = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadingPic, setUploadingPic] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
        
        // Load user
        const userRes = await fetch(`${backendUrl}/api/me`, {
          headers: { 'X-Dev-User': '647778438' }
        });
        
        if (userRes.ok) {
          const userData = await userRes.json();
          setUser(userData);
          console.log('✅ User loaded:', userData.display_name);
          
          // Load posts
          const postsRes = await fetch(`${backendUrl}/api/profile/posts`, {
            headers: { 'X-Dev-User': '647778438' }
          });
          
          if (postsRes.ok) {
            const postsData = await postsRes.json();
            setPosts(postsData);
            console.log('✅ Posts loaded:', postsData.length);
          }
        }
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);

  const handlePicUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploadingPic(true);
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
      alert('❌ Upload failed');
    } finally {
      setUploadingPic(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center">
      <div className="text-white text-xl">Loading...</div>
    </div>;
  }

  if (!user) {
    return <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center">
      <div className="text-white text-xl">User not found</div>
    </div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-500 to-blue-500 pb-20">
      {/* Header */}
      <div className="bg-purple-700/50 backdrop-blur-sm sticky top-0 z-10 px-4 py-3 flex items-center justify-between">
        <button onClick={() => navigate('/feed')} className="text-white text-2xl">←</button>
        <h1 className="text-white font-semibold text-lg">Profile</h1>
        <button className="text-white text-2xl">⋮</button>
      </div>

      <div className="px-4 py-6 space-y-4">
        {/* Main Profile Card */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          {/* Avatar & Name */}
          <div className="flex flex-col items-center mb-6">
            <div className="relative mb-3">
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-cyan-300 to-cyan-500 flex items-center justify-center overflow-hidden border-4 border-white shadow-lg">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Happy" alt="Avatar" className="w-full h-full" />
                )}
              </div>
              <label className="absolute bottom-0 right-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center cursor-pointer border-2 border-white shadow-md">
                <input type="file" accept="image/*" onChange={handlePicUpload} disabled={uploadingPic} className="hidden" />
                <span className="text-white text-sm">{uploadingPic ? '⏳' : '✓'}</span>
              </label>
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900">{user.display_name || 'Luvsociety'}</h2>
            <p className="text-sm text-gray-500">@{user.username || 'luvsociety'}</p>
            <p className="text-sm text-gray-600 mt-2 text-center px-4">{user.bio || 'Welcome to LuvHive! ✨'}</p>
          </div>

          {/* Mood & Stats Grid */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-pink-50 rounded-2xl p-4 text-center">
              <div className="text-2xl mb-1">😊</div>
              <div className="text-xs text-pink-600 font-semibold">Feeling Joyful</div>
            </div>
            <div className="bg-purple-50 rounded-2xl p-4 text-center">
              <div className="text-2xl mb-1">💜</div>
              <div className="text-xs text-purple-600 font-semibold">Vibe Purple</div>
            </div>
            <div className="bg-yellow-50 rounded-2xl p-4 text-center">
              <div className="text-2xl mb-1">✨</div>
              <div className="text-xs text-yellow-600 font-semibold">{posts.length} Sparks Given</div>
            </div>
            <div className="bg-orange-50 rounded-2xl p-4 text-center">
              <div className="text-2xl mb-1">💫</div>
              <div className="text-xs text-orange-600 font-semibold">Glows Received</div>
            </div>
          </div>

          {/* Additional Info */}
          <div className="space-y-3 mb-6">
            <div className="flex items-center text-sm text-gray-600">
              <span className="text-pink-500 mr-2">💗</span>
              <span>{user.followers_count || 0} Connections</span>
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <span className="text-green-500 mr-2">📊</span>
              <span>{Math.min(posts.length * 10, 100)}% Vibe Score</span>
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <span className="text-blue-500 mr-2">🌍</span>
              <span>Global Community</span>
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <span className="text-purple-500 mr-2">📅</span>
              <span>Joined {new Date(user.created_at || Date.now()).toLocaleDateString('en-US', {month: 'long', year: 'numeric'})}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button className="bg-gradient-to-r from-pink-500 to-purple-500 text-white py-3 rounded-full font-semibold shadow-md">
              Edit Profile
            </button>
            <button className="bg-gray-100 text-gray-700 py-3 rounded-full font-semibold shadow-sm">
              Settings
            </button>
          </div>
        </div>

        {/* Interests & Vibes */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <div className="flex items-center mb-4">
            <span className="text-xl mr-2">🎨</span>
            <h3 className="font-bold text-gray-900">Interests & Vibes</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="px-4 py-2 bg-green-100 text-green-700 rounded-full text-sm font-medium">Nature</div>
            <div className="px-4 py-2 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">Music</div>
            <div className="px-4 py-2 bg-pink-100 text-pink-700 rounded-full text-sm font-medium">Art</div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <div className="flex items-center mb-4">
            <span className="text-xl mr-2">📊</span>
            <h3 className="font-bold text-gray-900">Recent Activity</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center text-sm">
              <span className="text-2xl mr-3">✨</span>
              <div>
                <div className="font-semibold text-gray-900">Shared {posts.length} new posts</div>
                <div className="text-gray-500 text-xs">Recently active</div>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-2xl mr-3">💫</span>
              <div>
                <div className="font-semibold text-gray-900">Received glows</div>
                <div className="text-gray-500 text-xs">Your vibes are appreciated</div>
              </div>
            </div>
            <div className="flex items-center text-sm">
              <span className="text-2xl mr-3">💗</span>
              <div>
                <div className="font-semibold text-gray-900">Made connections</div>
                <div className="text-gray-500 text-xs">Building your community</div>
              </div>
            </div>
          </div>
        </div>

        {/* My Posts Section */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="font-bold text-gray-900 text-lg mb-4">My Posts ({posts.length})</h3>
          
          {posts.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-5xl mb-3">📝</div>
              <p className="text-gray-500 mb-4">No posts yet</p>
              <button onClick={() => navigate('/feed')} className="bg-purple-500 text-white px-6 py-2 rounded-full font-semibold shadow-md">
                Create Post
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <div key={post.id} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-300 to-cyan-500 flex-shrink-0 overflow-hidden">
                      {user.avatar_url ? (
                        <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                      ) : (
                        <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Happy" alt="Avatar" className="w-full h-full" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-gray-900">{user.display_name || 'Luvsociety'}</span>
                        <span className="text-xs text-gray-400">Just now</span>
                      </div>
                      
                      {post.content && (
                        <p className="text-gray-700 text-sm mb-2">{post.content}</p>
                      )}
                      
                      {post.media_urls && post.media_urls[0] ? (
                        <div className="rounded-2xl overflow-hidden mb-2">
                          <img
                            src={post.media_urls[0]}
                            alt="Post"
                            className="w-full h-auto object-cover"
                            onError={(e) => {
                              e.target.style.display = 'none';
                            }}
                          />
                        </div>
                      ) : null}
                      
                      <div className="flex items-center gap-4 text-gray-500 text-sm">
                        <button className="flex items-center gap-1 hover:text-pink-500">
                          <span>✨</span>
                          <span>{post.likes_count || 0}</span>
                        </button>
                        <button className="flex items-center gap-1 hover:text-blue-500">
                          <span>💬</span>
                          <span>{post.comments_count || 0}</span>
                        </button>
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
};

export default MyProfile;
