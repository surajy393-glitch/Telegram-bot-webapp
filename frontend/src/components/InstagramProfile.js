import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import EditProfile from './EditProfile';
import Settings from './Settings';

const InstagramProfile = ({ user }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('posts'); // 'posts', 'saved', 'followers', 'following'
  const [userPosts, setUserPosts] = useState([]);
  const [savedPosts, setSavedPosts] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    postsCount: 0,
    followersCount: 0,
    followingCount: 0
  });

  // Load user data on component mount
  useEffect(() => {
    if (user) {
      setCurrentUser(user);
      setLoading(false);
    } else {
      // Try to get user from localStorage
      const savedUser = localStorage.getItem('luvhive_user');
      if (savedUser) {
        try {
          const userData = JSON.parse(savedUser);
          setCurrentUser(userData);
          setLoading(false);
        } catch (error) {
          console.error('Error parsing user data:', error);
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    }
  }, [user]);

  useEffect(() => {
    if (currentUser) {
      loadUserData();
    }
  }, [currentUser]);

  // Live update listener for profile changes
  useEffect(() => {
    const onUpd = (e) => {
      setCurrentUser(e.detail);
      loadUserData(); // Reload data when profile updates
    };
    window.addEventListener('profile:updated', onUpd);
    return () => window.removeEventListener('profile:updated', onUpd);
  }, []);

  const loadUserData = () => {
    if (!currentUser) return;

    // Load user's posts with enhanced mock data
    const userPostsKey = `luvhive_posts_${currentUser.username}`;
    let posts = JSON.parse(localStorage.getItem(userPostsKey) || '[]');
    
    // Add mock posts if none exist
    if (posts.length === 0) {
      posts = [
        {
          id: 'user_post_1',
          image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400&h=300&fit=crop',
          likes: 45,
          comments: 12,
          type: 'image',
          content: 'Just joined LuvHive! Excited to connect with amazing people 🚀✨'
        },
        {
          id: 'user_post_2',
          image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop',
          likes: 67,
          comments: 8,
          type: 'image',
          content: 'Beautiful sunset today! Nature never fails to amaze me 🌅'
        },
        {
          id: 'user_post_3',
          image: 'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=400&h=300&fit=crop',
          likes: 89,
          comments: 23,
          type: 'image',
          content: 'Coffee and code - perfect combination for productivity! ☕💻'
        }
      ];
    }
    setUserPosts(posts);

    // Load saved posts with mock data
    const savedPostsKey = `luvhive_saved_${currentUser.username}`;
    let saved = JSON.parse(localStorage.getItem(savedPostsKey) || '[]');
    if (saved.length === 0) {
      saved = [
        {
          id: 'saved_1',
          image: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400',
          likes: 156,
          comments: 34,
          type: 'image',
          content: 'Amazing landscape photography tips! 📸',
          originalUser: 'PhotoPro'
        },
        {
          id: 'saved_2',
          image: 'https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=400',
          likes: 234,
          comments: 56,
          type: 'image',
          content: 'Motivational Monday vibes 💪✨',
          originalUser: 'MotivationDaily'
        }
      ];
    }
    setSavedPosts(saved);

    // Load followers with mock data
    const followersKey = `luvhive_followers_${currentUser.username}`;
    let followersList = JSON.parse(localStorage.getItem(followersKey) || '[]');
    if (followersList.length === 0) {
      followersList = [
        { username: 'alex_photographer', name: 'Alex Johnson', profilePic: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop' },
        { username: 'sarah_designer', name: 'Sarah Wilson', profilePic: 'https://images.unsplash.com/photo-1494790108755-2616b612b906?w=100&h=100&fit=crop' },
        { username: 'mike_traveler', name: 'Mike Chen', profilePic: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop' },
        { username: 'emma_artist', name: 'Emma Davis', profilePic: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop' }
      ];
    }
    setFollowers(followersList);

    // Load following with mock data
    const followingKey = `luvhive_following_${currentUser.username}`;
    let followingList = JSON.parse(localStorage.getItem(followingKey) || '[]');
    if (followingList.length === 0) {
      followingList = [
        { username: 'nature_lover', name: 'Nature Lover', profilePic: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop' },
        { username: 'tech_guru', name: 'Tech Guru', profilePic: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=100&h=100&fit=crop' }
      ];
    }
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

  const handleProfileUpdate = (updatedUser) => {
    setCurrentUser(updatedUser);
    // Update localStorage as well to ensure consistency
    localStorage.setItem('luvhive_user', JSON.stringify(updatedUser));
    setShowEditProfile(false);
    loadUserData(); // Refresh data
  };

  // Determine what to display based on active tab
  const getDisplayData = () => {
    switch (activeTab) {
      case 'posts':
        return userPosts;
      case 'saved':
        return savedPosts;
      case 'followers':
        return followers;
      case 'following':
        return following;
      default:
        return userPosts;
    }
  };

  const displayData = getDisplayData();

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center mb-4 animate-pulse mx-auto">
            <span className="text-2xl">👤</span>
          </div>
          <p className="text-gray-500 text-lg font-medium">Loading your profile...</p>
        </div>
      </div>
    );
  }

  // Show no user state
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="w-20 h-20 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center mb-6 mx-auto">
            <span className="text-3xl">👤</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">No Profile Found</h2>
          <p className="text-gray-600 mb-6">Please complete registration to create your profile.</p>
          <button
            onClick={() => navigate('/register')}
            className="bg-gradient-to-r from-pink-500 to-purple-600 text-white px-6 py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
          >
            Complete Registration
          </button>
        </div>
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
          
          <h1 className="text-xl font-bold">{currentUser.username}</h1>
          
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
                src={currentUser.profilePic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUser.name}`} 
                alt={currentUser.name} 
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.parentElement.innerHTML = `<div class="w-full h-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center text-white text-2xl font-bold">${currentUser.name?.[0] || '👤'}</div>`;
                }}
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
            <h2 className="text-lg font-bold text-gray-800 mb-1">{currentUser.name}</h2>
            {currentUser.bio && (
              <p className="text-gray-600 leading-relaxed">{currentUser.bio}</p>
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