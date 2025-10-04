import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import EditProfile from './EditProfile';
import Settings from './Settings';

const InstagramProfile = ({ user }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('posts'); // 'posts', 'saved'
  const [userPosts, setUserPosts] = useState([]);
  const [savedPosts, setSavedPosts] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [stats, setStats] = useState({
    postsCount: 0,
    followersCount: 0,
    followingCount: 0
  });

  useEffect(() => {
    if (user) {
      loadUserData();
    }
  }, [user]);

  const loadUserData = () => {
    // Load user's posts
    const userPostsKey = `luvhive_posts_${user.username}`;
    const posts = JSON.parse(localStorage.getItem(userPostsKey) || '[]');
    setUserPosts(posts);

    // Load saved posts
    const savedPostsKey = `luvhive_saved_${user.username}`;
    const saved = JSON.parse(localStorage.getItem(savedPostsKey) || '[]');
    setSavedPosts(saved);

    // Load followers
    const followersKey = `luvhive_followers_${user.username}`;
    const followersList = JSON.parse(localStorage.getItem(followersKey) || '[]');
    setFollowers(followersList);

    // Load following
    const followingKey = `luvhive_following_${user.username}`;
    const followingList = JSON.parse(localStorage.getItem(followingKey) || '[]');
    setFollowing(followingList);

    // Update stats
    setStats({
      postsCount: posts.length,
      followersCount: followersList.length,
      followingCount: followingList.length
    });
  };

  const handleSettingsUpdate = (newSettings) => {
    // Update user settings
    loadUserData(); // Refresh data
  };

  // Mock posts for demonstration (in real app, these would come from backend)
  const mockUserPosts = userPosts.length === 0 ? [
    {
      id: 1,
      image: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400',
      likes: 45,
      comments: 12,
      type: 'image'
    },
    {
      id: 2,
      image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',
      likes: 67,
      comments: 8,
      type: 'image'
    },
    {
      id: 3,
      image: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400',
      likes: 89,
      comments: 23,
      type: 'image'
    },
    {
      id: 4,
      image: 'https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=400',
      likes: 34,
      comments: 15,
      type: 'image'
    },
    {
      id: 5,
      image: 'https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400',
      likes: 56,
      comments: 9,
      type: 'image'
    },
    {
      id: 6,
      image: 'https://images.unsplash.com/photo-1512273222628-4daea6e55abb?w=400',
      likes: 78,
      comments: 21,
      type: 'image'
    }
  ] : userPosts;

  const displayPosts = activeTab === 'posts' ? mockUserPosts : savedPosts;

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-500">Please login to view profile</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate('/feed')}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <h1 className="text-xl font-bold">{user.username}</h1>
          
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto">
        {/* Profile Header */}
        <div className="p-4">
          <div className="flex items-center space-x-4 mb-6">
            {/* Profile Picture */}
            <div className="w-20 h-20 rounded-full overflow-hidden bg-gradient-to-r from-purple-400 to-pink-500 flex-shrink-0">
              <img 
                src={user.profilePic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.name}`} 
                alt={user.name} 
                className="w-full h-full object-cover" 
              />
            </div>

            {/* Stats */}
            <div className="flex-1 grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xl font-bold text-gray-800">{stats.postsCount}</div>
                <div className="text-sm text-gray-500">Posts</div>
              </div>
              <div>
                <div className="text-xl font-bold text-gray-800">{stats.followersCount}</div>
                <div className="text-sm text-gray-500">Followers</div>
              </div>
              <div>
                <div className="text-xl font-bold text-gray-800">{stats.followingCount}</div>
                <div className="text-sm text-gray-500">Following</div>
              </div>
            </div>
          </div>

          {/* Name & Bio */}
          <div className="mb-4">
            <h2 className="text-lg font-bold text-gray-800 mb-1">{user.name}</h2>
            {user.bio && (
              <p className="text-gray-600 leading-relaxed">{user.bio}</p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <button
              onClick={() => setShowEditProfile(true)}
              className="py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-2xl transition-colors"
            >
              Edit Profile
            </button>
            <button
              onClick={() => setShowSettings(true)}
              className="py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-2xl transition-colors"
            >
              Settings
            </button>
          </div>

          {/* Highlights/Stories */}
          <div className="flex space-x-4 mb-6 overflow-x-auto pb-2">
            <div className="flex-shrink-0 text-center">
              <div className="w-16 h-16 border-2 border-gray-300 border-dashed rounded-full flex items-center justify-center mb-1">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <p className="text-xs text-gray-500">New</p>
            </div>
            
            {/* Mock highlights */}
            {['Travel', 'Food', 'Friends', 'Work'].map((highlight, index) => (
              <div key={index} className="flex-shrink-0 text-center">
                <div className="w-16 h-16 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center mb-1">
                  <span className="text-white text-2xl">
                    {highlight === 'Travel' && '✈️'}
                    {highlight === 'Food' && '🍕'}
                    {highlight === 'Friends' && '👥'}
                    {highlight === 'Work' && '💻'}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{highlight}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Content Tabs */}
        <div className="border-t border-gray-200">
          <div className="flex">
            <button
              onClick={() => setActiveTab('posts')}
              className={`flex-1 py-4 flex items-center justify-center border-b-2 transition-colors ${
                activeTab === 'posts'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M21 8.75H3A.75.75 0 012.25 8V6A3.75 3.75 0 016 2.25h12A3.75 3.75 0 0121.75 6v2a.75.75 0 01-.75.75zm0 0v7.5A3.75 3.75 0 0117.25 20H6.75A3.75 3.75 0 013 16.25V8.75M8.5 12.5h7" />
              </svg>
            </button>
            <button
              onClick={() => setActiveTab('saved')}
              className={`flex-1 py-4 flex items-center justify-center border-b-2 transition-colors ${
                activeTab === 'saved'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Posts Grid */}
        <div className="p-1">
          {displayPosts.length > 0 ? (
            <div className="grid grid-cols-3 gap-1">
              {displayPosts.map((post, index) => (
                <div key={index} className="relative aspect-square">
                  <img 
                    src={post.image} 
                    alt="Post" 
                    className="w-full h-full object-cover hover:opacity-90 transition-opacity cursor-pointer"
                  />
                  <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded-full">
                    ✨{post.likes}
                  </div>
                  {post.type === 'video' && (
                    <div className="absolute bottom-2 right-2 text-white">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-24 h-24 border-2 border-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                {activeTab === 'posts' ? 'No Posts Yet' : 'No Saved Posts'}
              </h3>
              <p className="text-gray-500 mb-4">
                {activeTab === 'posts' 
                  ? 'Start sharing your moments with the world!' 
                  : 'Save posts you love to view them here later.'
                }
              </p>
              {activeTab === 'posts' && (
                <button
                  onClick={() => navigate('/feed')}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all"
                >
                  Create Your First Post ✨
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showEditProfile && (
        <EditProfile
          user={user}
          onClose={() => setShowEditProfile(false)}
          onProfileUpdated={() => {
            setShowEditProfile(false);
            // Refresh user data
            window.location.reload();
          }}
        />
      )}

      {showSettings && (
        <Settings
          user={user}
          onClose={() => setShowSettings(false)}
          onSettingsUpdate={handleSettingsUpdate}
        />
      )}
    </div>
  );
};

export default InstagramProfile;