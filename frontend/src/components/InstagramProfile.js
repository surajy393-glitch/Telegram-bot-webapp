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
  }, [currentUser]); // Only re-run when currentUser changes

  // Live update listener for profile changes
  useEffect(() => {
    const onUpd = (e) => {
      setCurrentUser(e.detail);
      loadUserData(); // Reload data when profile updates
    };
    window.addEventListener('profile:updated', onUpd);
    return () => window.removeEventListener('profile:updated', onUpd);
  }, []);

  const loadUserData = async () => {
    if (!currentUser) return;

    try {
      // Fetch user posts from backend API
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      console.log('🔍 Fetching profile posts from backend...');
      
      const response = await fetch(`${backendUrl}/api/profile/posts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });

      if (response.ok) {
        const postsData = await response.json();
        console.log('✅ Fetched posts from backend:', postsData);
        
        // Transform backend posts to component format
        const transformedPosts = postsData.map(post => ({
          id: post.id || post._id,
          image: post.images?.[0] || post.image || post.video,
          likes: post.likes?.length || 0,
          comments: post.comments?.length || 0,
          type: post.video ? 'video' : 'image',
          content: post.content || ''
        }));
        
        setUserPosts(transformedPosts);
        
        // Update stats with fetched posts count
        setStats(prevStats => ({
          ...prevStats,
          postsCount: transformedPosts.length
        }));
      } else {
        console.error('❌ Failed to fetch posts, status:', response.status);
        setUserPosts([]);
      }
    } catch (error) {
      console.error('❌ Error fetching profile posts:', error);
      setUserPosts([]);
    }

    // Load saved posts, followers, following from localStorage (keep existing functionality)
    const username = currentUser.username || currentUser.name || 'user';
    const savedPostsKey = `luvhive_saved_${username}`;
    const saved = JSON.parse(localStorage.getItem(savedPostsKey) || '[]');
    setSavedPosts(saved);

    const followersKey = `luvhive_followers_${username}`;
    const followersList = JSON.parse(localStorage.getItem(followersKey) || '[]');
    setFollowers(followersList);

    const followingKey = `luvhive_following_${username}`;
    const followingList = JSON.parse(localStorage.getItem(followingKey) || '[]');
    setFollowing(followingList);

    // Update stats - followers and following counts (posts count updated above)
    setStats(prevStats => ({
      ...prevStats,
      followersCount: followersList.length,
      followingCount: followingList.length
    }));
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
              <button 
                onClick={() => setActiveTab('posts')}
                className="transition-colors hover:bg-gray-50 rounded-lg p-2"
              >
                <div className="text-xl font-bold text-gray-800">{stats.postsCount}</div>
                <div className="text-sm text-gray-500">Posts</div>
              </button>
              <button 
                onClick={() => setActiveTab('followers')}
                className="transition-colors hover:bg-gray-50 rounded-lg p-2"
              >
                <div className="text-xl font-bold text-gray-800">{stats.followersCount}</div>
                <div className="text-sm text-gray-500">Followers</div>
              </button>
              <button 
                onClick={() => setActiveTab('following')}
                className="transition-colors hover:bg-gray-50 rounded-lg p-2"
              >
                <div className="text-xl font-bold text-gray-800">{stats.followingCount}</div>
                <div className="text-sm text-gray-500">Following</div>
              </button>
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

        {/* Content Tabs - Posts, Saved, Followers, Following */}
        <div className="border-t border-gray-200">
          <div className="grid grid-cols-4">
            <button
              onClick={() => setActiveTab('posts')}
              className={`py-4 flex flex-col items-center justify-center border-b-2 transition-colors ${
                activeTab === 'posts'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M21 8.75H3A.75.75 0 012.25 8V6A3.75 3.75 0 016 2.25h12A3.75 3.75 0 0121.75 6v2a.75.75 0 01-.75.75zm0 0v7.5A3.75 3.75 0 0117.25 20H6.75A3.75 3.75 0 013 16.25V8.75M8.5 12.5h7" />
              </svg>
              <span className="text-xs">Posts</span>
            </button>
            <button
              onClick={() => setActiveTab('saved')}
              className={`py-4 flex flex-col items-center justify-center border-b-2 transition-colors ${
                activeTab === 'saved'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              <span className="text-xs">Saved</span>
            </button>
            <button
              onClick={() => setActiveTab('followers')}
              className={`py-4 flex flex-col items-center justify-center border-b-2 transition-colors ${
                activeTab === 'followers'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <span className="text-xs">Followers</span>
            </button>
            <button
              onClick={() => setActiveTab('following')}
              className={`py-4 flex flex-col items-center justify-center border-b-2 transition-colors ${
                activeTab === 'following'
                  ? 'border-gray-800 text-gray-800'
                  : 'border-transparent text-gray-400'
              }`}
            >
              <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="text-xs">Following</span>
            </button>
          </div>
        </div>

        {/* Content Display */}
        <div className="p-4">
          {activeTab === 'posts' || activeTab === 'saved' ? (
            // Posts Grid Layout
            displayData.length > 0 ? (
              <div className="grid grid-cols-3 gap-1">
                {displayData.map((post, index) => (
                  <div key={index} className="relative aspect-square">
                    <img 
                      src={post.image} 
                      alt="Post" 
                      className="w-full h-full object-cover hover:opacity-90 transition-opacity cursor-pointer rounded-lg"
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
            )
          ) : (
            // Followers/Following List Layout
            displayData.length > 0 ? (
              <div className="space-y-3">
                {displayData.map((person, index) => (
                  <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-2xl hover:bg-gray-100 transition-colors">
                    <div className="w-12 h-12 rounded-full overflow-hidden bg-gradient-to-r from-purple-400 to-pink-500 flex-shrink-0">
                      <img 
                        src={person.profilePic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${person.name}`} 
                        alt={person.name} 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          if (e.target && e.target.parentElement) {
                            const initial = person.name?.[0]?.toUpperCase() || '👤';
                            e.target.style.display = 'none';
                            
                            // Create fallback div safely
                            const fallbackDiv = document.createElement('div');
                            fallbackDiv.className = 'w-full h-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center text-white text-lg font-bold rounded-full';
                            fallbackDiv.textContent = initial;
                            
                            if (e.target.parentElement) {
                              e.target.parentElement.appendChild(fallbackDiv);
                            }
                          }
                        }}
                      />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800">{person.name}</h4>
                      <p className="text-sm text-gray-500">@{person.username}</p>
                    </div>
                    <button className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full text-sm font-semibold hover:shadow-md transition-all">
                      {activeTab === 'followers' ? 'Follow Back' : 'Unfollow'}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-24 h-24 border-2 border-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  No {activeTab === 'followers' ? 'Followers' : 'Following'} Yet
                </h3>
                <p className="text-gray-500 mb-4">
                  {activeTab === 'followers' 
                    ? 'Start connecting with people and they\'ll appear here!' 
                    : 'Follow people you\'re interested in to see them here.'
                  }
                </p>
                <button
                  onClick={() => navigate('/discover')}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all"
                >
                  Discover People ✨
                </button>
              </div>
            )
          )}
        </div>
      </div>

      {/* Modals */}
      {showEditProfile && (
        <EditProfile
          user={currentUser}
          onClose={() => setShowEditProfile(false)}
          onSave={handleProfileUpdate}
        />
      )}

      {showSettings && (
        <Settings
          user={currentUser}
          onClose={() => setShowSettings(false)}
          onSettingsUpdate={handleSettingsUpdate}
        />
      )}
    </div>
  );
};

export default InstagramProfile;