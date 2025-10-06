import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Settings from './Settings';
import Avatar from './ui/Avatar';

const MyProfile = ({ user }) => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [userPosts, setUserPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all'); // all, photos, videos
  const [showSettings, setShowSettings] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedBio, setEditedBio] = useState('');
  const [uploadingPic, setUploadingPic] = useState(false);
  const [stats, setStats] = useState({
    posts: 0,
    sparks: 0,
    glows: 0,
    vibeScore: 0
  });

  // Load user data
  useEffect(() => {
    const loadUser = async () => {
      if (user) {
        setCurrentUser(user);
      } else {
        const savedUser = localStorage.getItem('luvhive_user');
        if (savedUser) {
          try {
            setCurrentUser(JSON.parse(savedUser));
          } catch (error) {
            console.error('Error parsing user:', error);
          }
        }
      }
      setLoading(false);
    };
    loadUser();
  }, [user]);

  // Fetch user posts from backend
  useEffect(() => {
    const fetchPosts = async () => {
      if (!currentUser) return;

      try {
        const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
        console.log('🔍 Fetching profile posts from:', `${backendUrl}/api/profile/posts`);
        
        const response = await fetch(`${backendUrl}/api/profile/posts`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...(window.Telegram?.WebApp?.initData ? {
              'X-Telegram-Init-Data': window.Telegram.WebApp.initData
            } : {}),
            // Dev mode authentication
            'X-Dev-User': currentUser.tg_user_id || currentUser.id || '647778438'
          },
          credentials: 'include'
        });

        if (response.ok) {
          const posts = await response.json();
          console.log('✅ Fetched posts:', posts);
          
          // Transform posts to match frontend expectations
          const transformedPosts = posts.map(post => ({
            ...post,
            images: post.media_urls || post.images || [], // Map media_urls to images
            video: post.video || (post.media_urls && post.media_urls.find(url => url.includes('.mp4') || url.includes('video'))) || null
          }));
          
          setUserPosts(transformedPosts);
          
          // Calculate stats from posts
          const totalSparks = posts.reduce((sum, post) => sum + (post.likes?.length || post.likes_count || 0), 0);
          const totalComments = posts.reduce((sum, post) => sum + (post.comments?.length || post.comments_count || 0), 0);
          
          setStats({
            posts: posts.length,
            sparks: totalSparks,
            glows: totalComments,
            vibeScore: Math.min(100, (totalSparks + totalComments) * 2)
          });
        } else {
          console.error('Failed to fetch posts:', response.status);
        }
      } catch (error) {
        console.error('Error fetching posts:', error);
      }
    };

    fetchPosts();
  }, [currentUser]);

  const handleBioSave = async () => {
    if (!currentUser) return;

    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const response = await fetch(`${backendUrl}/api/onboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(window.Telegram?.WebApp?.initData ? {
            'X-Telegram-Init-Data': window.Telegram.WebApp.initData
          } : {}),
          'X-Dev-User': currentUser.tg_user_id || currentUser.id || '647778438'
        },
        body: JSON.stringify({
          ...currentUser,
          bio: editedBio
        }),
        credentials: 'include'
      });

      if (response.ok) {
        const updatedUser = { ...currentUser, bio: editedBio };
        setCurrentUser(updatedUser);
        localStorage.setItem('luvhive_user', JSON.stringify(updatedUser));
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Error updating bio:', error);
    }
  };

  const handlePictureUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !currentUser) return;

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }

    // Check file type
    if (!file.type.startsWith('image/')) {
      alert('Please upload an image file');
      return;
    }

    setUploadingPic(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const response = await fetch(`${backendUrl}/api/upload-photo`, {
        method: 'POST',
        headers: {
          ...(window.Telegram?.WebApp?.initData ? {
            'X-Telegram-Init-Data': window.Telegram.WebApp.initData
          } : {}),
          'X-Dev-User': currentUser.tg_user_id || currentUser.id || '647778438'
        },
        body: formData,
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        const updatedUser = { ...currentUser, avatarUrl: data.url, avatar_url: data.url };
        setCurrentUser(updatedUser);
        localStorage.setItem('luvhive_user', JSON.stringify(updatedUser));
        alert('Profile picture updated successfully! ✨');
      } else {
        const error = await response.text();
        alert('Failed to upload picture: ' + error);
      }
    } catch (error) {
      console.error('Error uploading picture:', error);
      alert('Failed to upload picture. Please try again.');
    } finally {
      setUploadingPic(false);
    }
  };

  // Filter posts
  const filteredPosts = userPosts.filter(post => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'photos') return post.images && post.images.length > 0;
    if (activeFilter === 'videos') return post.video;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600 flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 border-4 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white text-lg font-medium">Loading your vibe...</p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="text-6xl mb-6">😕</div>
          <h2 className="text-3xl font-bold text-white mb-4">No Profile Found</h2>
          <p className="text-white/80 mb-6">Please complete registration to create your profile.</p>
          <button
            onClick={() => navigate('/register')}
            className="bg-white text-purple-900 px-8 py-4 rounded-2xl font-bold text-lg hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
          >
            Create Profile
          </button>
        </div>
      </div>
    );
  }

  const userData = {
    name: currentUser.name || currentUser.display_name || 'LuvHive User',
    username: currentUser.username || currentUser.name || 'user',
    bio: currentUser.bio || 'Living my best life on LuvHive! ✨',
    avatarUrl: currentUser.avatarUrl || currentUser.avatar_url || currentUser.profilePic,
    mood: currentUser.mood || '😊',
    joinedDate: currentUser.created_at || currentUser.joinDate || 'Recently'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-pink-800 to-orange-600">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-black/30 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-4">
          <button
            onClick={() => navigate('/feed')}
            className="p-3 rounded-full bg-white/10 hover:bg-white/20 transition-all"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <h1 className="text-2xl font-bold text-white">My Vibe Profile</h1>
          
          <button
            onClick={() => setShowSettings(true)}
            className="p-3 rounded-full bg-white/10 hover:bg-white/20 transition-all"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Hero Profile Card */}
        <div className="relative mb-8">
          {/* Glassmorphism Card */}
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl">
            {/* Profile Header */}
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6 mb-8">
              {/* Avatar with Gradient Ring */}
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-yellow-400 via-pink-500 to-purple-500 rounded-full blur opacity-75 animate-pulse"></div>
                <div className="relative w-32 h-32 rounded-full overflow-hidden border-4 border-white/30 bg-gradient-to-br from-purple-400 to-pink-500">
                  {userData.avatarUrl ? (
                    <img 
                      src={userData.avatarUrl} 
                      alt={userData.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-5xl">
                      {userData.mood}
                    </div>
                  )}
                </div>
                {/* Online Status Badge */}
                <div className="absolute bottom-2 right-2 w-6 h-6 bg-green-400 rounded-full border-4 border-white flex items-center justify-center">
                  <span className="text-xs">✨</span>
                </div>
              </div>

              {/* User Info */}
              <div className="flex-1 text-center md:text-left">
                <h2 className="text-3xl font-bold text-white mb-2">{userData.name}</h2>
                <p className="text-xl text-purple-200 mb-4">@{userData.username}</p>
                
                {/* Bio Section */}
                {isEditing ? (
                  <div className="space-y-3">
                    <textarea
                      value={editedBio}
                      onChange={(e) => setEditedBio(e.target.value)}
                      className="w-full bg-white/10 backdrop-blur-lg text-white placeholder-white/50 rounded-2xl px-4 py-3 border border-white/20 focus:outline-none focus:border-pink-400 transition-all"
                      rows="3"
                      placeholder="Tell us about yourself..."
                    />
                    <div className="flex gap-3">
                      <button
                        onClick={handleBioSave}
                        className="flex-1 bg-gradient-to-r from-pink-500 to-purple-600 text-white px-6 py-3 rounded-2xl font-bold hover:shadow-lg transform hover:scale-105 transition-all"
                      >
                        Save Bio
                      </button>
                      <button
                        onClick={() => setIsEditing(false)}
                        className="px-6 py-3 bg-white/10 backdrop-blur-lg text-white rounded-2xl font-semibold hover:bg-white/20 transition-all"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-white/90 text-lg leading-relaxed mb-3">{userData.bio}</p>
                    <button
                      onClick={() => {
                        setEditedBio(userData.bio);
                        setIsEditing(true);
                      }}
                      className="text-pink-300 hover:text-pink-200 font-semibold text-sm flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                      Edit Bio
                    </button>
                  </div>
                )}

                {/* Join Date */}
                <div className="mt-4 flex items-center gap-2 text-white/70">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span>Joined {userData.joinedDate}</span>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gradient-to-br from-yellow-400/20 to-orange-500/20 backdrop-blur-lg rounded-2xl p-4 border border-white/10 text-center transform hover:scale-105 transition-all">
                <div className="text-4xl font-bold text-yellow-300 mb-1">{stats.posts}</div>
                <div className="text-white/80 text-sm font-semibold">Posts</div>
              </div>
              <div className="bg-gradient-to-br from-pink-400/20 to-red-500/20 backdrop-blur-lg rounded-2xl p-4 border border-white/10 text-center transform hover:scale-105 transition-all">
                <div className="text-4xl font-bold text-pink-300 mb-1">{stats.sparks}</div>
                <div className="text-white/80 text-sm font-semibold">✨ Sparks</div>
              </div>
              <div className="bg-gradient-to-br from-purple-400/20 to-indigo-500/20 backdrop-blur-lg rounded-2xl p-4 border border-white/10 text-center transform hover:scale-105 transition-all">
                <div className="text-4xl font-bold text-purple-300 mb-1">{stats.glows}</div>
                <div className="text-white/80 text-sm font-semibold">💫 Glows</div>
              </div>
              <div className="bg-gradient-to-br from-green-400/20 to-emerald-500/20 backdrop-blur-lg rounded-2xl p-4 border border-white/10 text-center transform hover:scale-105 transition-all">
                <div className="text-4xl font-bold text-green-300 mb-1">{stats.vibeScore}%</div>
                <div className="text-white/80 text-sm font-semibold">🌈 Vibe</div>
              </div>
            </div>
          </div>
        </div>

        {/* Posts Section */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 border border-white/20">
          {/* Filter Tabs */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-white">My Posts</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setActiveFilter('all')}
                className={`px-4 py-2 rounded-xl font-semibold transition-all ${
                  activeFilter === 'all'
                    ? 'bg-white text-purple-900'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setActiveFilter('photos')}
                className={`px-4 py-2 rounded-xl font-semibold transition-all ${
                  activeFilter === 'photos'
                    ? 'bg-white text-purple-900'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                📸 Photos
              </button>
              <button
                onClick={() => setActiveFilter('videos')}
                className={`px-4 py-2 rounded-xl font-semibold transition-all ${
                  activeFilter === 'videos'
                    ? 'bg-white text-purple-900'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                🎥 Videos
              </button>
            </div>
          </div>

          {/* Posts Grid */}
          {filteredPosts.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-7xl mb-6">📝</div>
              <h3 className="text-2xl font-bold text-white mb-3">No Posts Yet</h3>
              <p className="text-white/70 text-lg mb-6">Start sharing your vibes with the world!</p>
              <button
                onClick={() => navigate('/feed')}
                className="bg-gradient-to-r from-pink-500 to-purple-600 text-white px-8 py-4 rounded-2xl font-bold text-lg hover:shadow-2xl transform hover:scale-105 transition-all"
              >
                Create Your First Post ✨
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredPosts.map((post, index) => (
                <div
                  key={post.id || index}
                  className="relative aspect-square rounded-2xl overflow-hidden group cursor-pointer transform hover:scale-105 transition-all duration-300"
                >
                  {/* Post Image/Video */}
                  {post.images && post.images[0] ? (
                    <img
                      src={post.images[0]}
                      alt="Post"
                      className="w-full h-full object-cover"
                    />
                  ) : post.video ? (
                    <video
                      src={post.video}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center p-4">
                      <p className="text-white text-center font-medium line-clamp-4">{post.content}</p>
                    </div>
                  )}

                  {/* Overlay on Hover */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                    <div className="text-center text-white">
                      <div className="flex items-center justify-center gap-4 mb-2">
                        <div className="flex items-center gap-1">
                          <span className="text-2xl">✨</span>
                          <span className="font-bold">{post.likes?.length || 0}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-2xl">💬</span>
                          <span className="font-bold">{post.comments?.length || 0}</span>
                        </div>
                      </div>
                      {post.video && (
                        <div className="text-sm">🎥 Video</div>
                      )}
                    </div>
                  </div>

                  {/* Media Type Badge */}
                  {post.video && (
                    <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm text-white px-3 py-1 rounded-full text-sm font-semibold">
                      🎥 Video
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <Settings
          user={userData}
          onClose={() => setShowSettings(false)}
          onSettingsUpdate={() => {}}
        />
      )}
    </div>
  );
};

export default MyProfile;
