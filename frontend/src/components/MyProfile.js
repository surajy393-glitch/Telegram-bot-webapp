import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const MyProfile = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadingPic, setUploadingPic] = useState(false);

  // Load user from backend
  useEffect(() => {
    const loadData = async () => {
      try {
        // Get user
        const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
        const userRes = await fetch(`${backendUrl}/api/me`, {
          headers: {
            'X-Dev-User': '647778438'
          }
        });
        
        if (userRes.ok) {
          const userData = await userRes.json();
          setUser(userData);
          console.log('✅ User loaded:', userData.display_name);
          
          // Get posts
          const postsRes = await fetch(`${backendUrl}/api/profile/posts`, {
            headers: {
              'X-Dev-User': '647778438'
            }
          });
          
          if (postsRes.ok) {
            const postsData = await postsRes.json();
            setPosts(postsData);
            console.log('✅ Posts loaded:', postsData.length);
          }
        }
      } catch (error) {
        console.error('Error loading data:', error);
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
        headers: {
          'X-Dev-User': '647778438'
        },
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setUser({...user, avatar_url: data.photo_url});
        alert('✅ Profile picture updated!');
      }
    } catch (error) {
      alert('❌ Upload failed');
    } finally {
      setUploadingPic(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600 flex items-center justify-center">
        <div className="text-white text-2xl">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600 flex items-center justify-center">
        <div className="text-white text-2xl">User not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600 p-4">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-6">
        <button
          onClick={() => navigate('/feed')}
          className="text-white text-2xl mb-4"
        >
          ← Back
        </button>
        <h1 className="text-3xl font-bold text-white">My Profile</h1>
      </div>

      {/* Profile Card */}
      <div className="max-w-4xl mx-auto bg-white/10 backdrop-blur-lg rounded-3xl p-6 mb-6">
        {/* Avatar Section */}
        <div className="flex items-center gap-6 mb-6">
          <div className="relative">
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center overflow-hidden">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <span className="text-5xl text-white">{user.display_name?.[0] || '👤'}</span>
              )}
            </div>
            
            {/* Upload Button */}
            <label className="absolute bottom-0 right-0 w-10 h-10 bg-pink-500 rounded-full flex items-center justify-center cursor-pointer hover:bg-pink-600">
              <input
                type="file"
                accept="image/*"
                onChange={handlePicUpload}
                disabled={uploadingPic}
                className="hidden"
              />
              {uploadingPic ? '⏳' : '📷'}
            </label>
          </div>
          
          <div>
            <h2 className="text-2xl font-bold text-white">{user.display_name}</h2>
            <p className="text-white/80">@{user.username}</p>
            <p className="text-white/70 mt-2">{user.bio || 'No bio yet'}</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white/10 rounded-2xl p-4 text-center">
            <div className="text-3xl font-bold text-white">{posts.length}</div>
            <div className="text-white/80">Posts</div>
          </div>
          <div className="bg-white/10 rounded-2xl p-4 text-center">
            <div className="text-3xl font-bold text-white">{user.followers_count || 0}</div>
            <div className="text-white/80">Followers</div>
          </div>
          <div className="bg-white/10 rounded-2xl p-4 text-center">
            <div className="text-3xl font-bold text-white">{user.following_count || 0}</div>
            <div className="text-white/80">Following</div>
          </div>
        </div>
      </div>

      {/* Posts Section */}
      <div className="max-w-4xl mx-auto bg-white/10 backdrop-blur-lg rounded-3xl p-6">
        <h3 className="text-2xl font-bold text-white mb-4">My Posts ({posts.length})</h3>
        
        {posts.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📝</div>
            <p className="text-white text-xl">No posts yet</p>
            <button
              onClick={() => navigate('/feed')}
              className="mt-4 bg-pink-500 text-white px-6 py-3 rounded-full font-bold hover:bg-pink-600"
            >
              Create First Post
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {posts.map((post) => (
              <div
                key={post.id}
                className="aspect-square rounded-2xl overflow-hidden bg-gray-800 relative group"
              >
                {post.media_urls && post.media_urls[0] ? (
                  <img
                    src={post.media_urls[0]}
                    alt="Post"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-purple-500 to-pink-500 p-4"><p class="text-white text-center font-medium text-sm">${post.content?.substring(0, 50) || 'Post'}...</p></div>`;
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-purple-500 to-pink-500 p-4">
                    <p className="text-white text-center font-medium text-sm">
                      {post.content?.substring(0, 80) || 'Post'}
                    </p>
                  </div>
                )}
                
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="text-white text-center">
                    <div className="flex gap-4 justify-center">
                      <span>❤️ {post.likes_count || 0}</span>
                      <span>💬 {post.comments_count || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyProfile;
