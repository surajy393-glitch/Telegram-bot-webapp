import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import EditProfile from './EditProfile';
import Settings from './Settings';

const UserProfile = ({ user, theme }) => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Load user data on component mount
  useEffect(() => {
    // First try the passed user prop
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
          // Show error instead of redirect
        }
      } else {
        setLoading(false);
        // Show no user state instead of redirect
      }
    }
  }, [user]);

  const handleEditProfile = () => {
    setShowEditProfile(true);
  };

  const handleSettings = () => {
    setShowSettings(true);
  };

  const handleProfileUpdate = (updatedUser) => {
    setCurrentUser(updatedUser);
    // Also update the parent component's user state if needed
    if (user) {
      // This would typically call a parent callback to update user state
    }
  };

  const handleSettingsUpdate = (newSettings) => {
    const updatedUser = {
      ...currentUser,
      settings: newSettings,
      isPublic: newSettings.isPublic
    };
    setCurrentUser(updatedUser);
  };

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-600 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-4 animate-pulse-love mx-auto">
            <span className="text-2xl animate-heart-beat">👤</span>
          </div>
          <p className="text-white text-lg font-medium">Loading your profile...</p>
        </div>
      </div>
    );
  }

  // Show no user state
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-600 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mb-6 animate-pulse-love mx-auto">
            <span className="text-3xl">👤</span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">No Profile Found</h2>
          <p className="text-white/80 mb-6">Please complete registration to create your profile.</p>
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

  // Use current user data with proper fallbacks
  const userData = {
    name: currentUser.name || 'LuvHive User',
    username: currentUser.username || 'user', 
    bio: currentUser.bio || 'Welcome to LuvHive! ✨',
    location: currentUser.location || 'Global Community',
    joinDate: currentUser.joinDate || 'Recently',
    stats: currentUser.stats || {
      sparks: 0,
      glows: 0,
      connections: 0,
      vibeScore: 85
    },
    interests: currentUser.interests || ['Nature', 'Music', 'Art'],
    mood: currentUser.mood || 'happy',
    aura: currentUser.aura || 'golden', 
    recentPosts: currentUser.recentPosts || 0,
    profilePic: currentUser.profilePic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUser.name || 'default'}`
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-600">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-white/10 backdrop-blur-lg border-b border-white/20">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate('/feed')}
            className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <h1 className="text-xl font-bold text-white">Profile</h1>
          
          <button className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 py-6">
        {/* Profile Card */}
        <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-2xl mb-6">
            <div className="text-center mb-6">
              <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center relative">
                {userData.profilePic ? (
                  <img src={userData.profilePic} alt={userData.name} className="w-full h-full rounded-full object-cover" />
                ) : (
                  <span className="text-4xl">🌙</span>
                )}
                <div className="absolute -bottom-1 -right-1 w-8 h-8 bg-green-400 rounded-full border-4 border-white flex items-center justify-center">
                  <span className="text-xs">✨</span>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-1">{userData.name}</h2>
              <p className="text-purple-600 font-medium mb-2">@{userData.username}</p>
              <p className="text-gray-600 text-sm leading-relaxed">{userData.bio}</p>
            </div>

            {/* Current Mood & Aura */}
            <div className="flex items-center justify-center space-x-4 mb-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mb-1">
                  <span className="text-lg">🧠</span>
                </div>
                <p className="text-xs text-gray-500 font-medium">Mood</p>
                <p className="text-sm text-purple-600 capitalize">{userData.mood}</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mb-1">
                  <span className="text-lg">🌌</span>
                </div>
                <p className="text-xs text-gray-500 font-medium">Aura</p>
                <p className="text-sm text-indigo-600 capitalize">{userData.aura}</p>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="text-center p-3 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-2xl">
                <div className="text-2xl font-bold text-orange-600 mb-1">{userData.stats.sparks}</div>
                <div className="text-xs text-gray-600">✨ Sparks Given</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-r from-pink-50 to-purple-50 rounded-2xl">
                <div className="text-2xl font-bold text-purple-600 mb-1">{userData.stats.glows}</div>
                <div className="text-xs text-gray-600">💫 Glows Received</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl">
                <div className="text-2xl font-bold text-indigo-600 mb-1">{userData.stats.connections}</div>
                <div className="text-xs text-gray-600">💕 Connections</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl">
                <div className="text-2xl font-bold text-emerald-600 mb-1">{userData.stats.vibeScore}%</div>
                <div className="text-xs text-gray-600">🌈 Vibe Score</div>
              </div>
            </div>

            {/* Location & Join Date */}
            <div className="flex items-center justify-between text-sm text-gray-500 mb-6">
              <div className="flex items-center space-x-1">
                <span>📍</span>
                <span>{userData.location}</span>
              </div>
              <div className="flex items-center space-x-1">
                <span>📅</span>
                <span>Joined {userData.joinDate}</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-3">
              <button 
                onClick={handleEditProfile}
                className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
              >
                Edit Profile
              </button>
              <button 
                onClick={handleSettings}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-600 py-3 rounded-2xl font-semibold transition-all duration-200"
              >
                Settings
              </button>
            </div>
        </div>

        {/* Interests */}
        <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl mb-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">🎯</span>
            Interests & Vibes
          </h3>
          <div className="flex flex-wrap gap-2">
            {userData.interests.map((interest, index) => (
              <span
                key={index}
                className="px-3 py-2 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-sm font-medium rounded-full hover:shadow-md transition-all duration-200"
              >
                {interest}
              </span>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">📊</span>
            Recent Activity
          </h3>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                <span>✨</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">Shared {userData.recentPosts} new posts</p>
                <p className="text-xs text-gray-500">Recently active</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                <span>💫</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">Received {userData.stats.glows} glows</p>
                <p className="text-xs text-gray-500">Your vibes are appreciated!</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                <span>💕</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">Made {userData.stats.connections} connections</p>
                <p className="text-xs text-gray-500">Building your community</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showEditProfile && (
        <EditProfile
          user={userData}
          onClose={() => setShowEditProfile(false)}
          onSave={handleProfileUpdate}
        />
      )}

      {showSettings && (
        <Settings
          user={userData}
          onClose={() => setShowSettings(false)}
          onSettingsUpdate={handleSettingsUpdate}
        />
      )}
    </div>
  );
};

export default UserProfile;