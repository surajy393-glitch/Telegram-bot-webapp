import React, { useState, useEffect } from 'react';
import { showAlert, closeTelegramWebApp } from '../utils/telegram';

const ViewUserProfile = ({ targetUser, currentUser, onClose }) => {
  const [isFollowing, setIsFollowing] = useState(false);
  const [followerCount, setFollowerCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [userPosts, setUserPosts] = useState([]);

  useEffect(() => {
    if (targetUser && currentUser) {
      // Check if already following
      const followingData = localStorage.getItem(`luvhive_following_${currentUser.username}`);
      if (followingData) {
        try {
          const following = JSON.parse(followingData);
          setIsFollowing(following.includes(targetUser.username));
        } catch (error) {
          console.error('Error loading following data:', error);
        }
      }

      // Load follower count
      const followersData = localStorage.getItem(`luvhive_followers_${targetUser.username}`);
      if (followersData) {
        try {
          const followers = JSON.parse(followersData);
          setFollowerCount(followers.length);
        } catch (error) {
          setFollowerCount(Math.floor(Math.random() * 500) + 50); // Mock data
        }
      } else {
        setFollowerCount(Math.floor(Math.random() * 500) + 50); // Mock data
      }

      // Load user posts (mock data)
      const mockPosts = [
        {
          id: 1,
          image: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=300',
          likes: 45,
          comments: 12
        },
        {
          id: 2,
          image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300',
          likes: 67,
          comments: 8
        },
        {
          id: 3,
          image: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=300',
          likes: 89,
          comments: 23
        }
      ];
      setUserPosts(mockPosts);
    }
  }, [targetUser, currentUser]);

  const handleFollowToggle = async () => {
    if (!currentUser || !targetUser) return;

    setIsLoading(true);
    
    try {
      // Update following list for current user
      const followingKey = `luvhive_following_${currentUser.username}`;
      let following = [];
      
      const existingFollowing = localStorage.getItem(followingKey);
      if (existingFollowing) {
        following = JSON.parse(existingFollowing);
      }

      if (isFollowing) {
        // Unfollow
        following = following.filter(username => username !== targetUser.username);
        setFollowerCount(prev => Math.max(0, prev - 1));
      } else {
        // Follow
        if (!following.includes(targetUser.username)) {
          following.push(targetUser.username);
          setFollowerCount(prev => prev + 1);
        }
      }

      localStorage.setItem(followingKey, JSON.stringify(following));

      // Update followers list for target user
      const followersKey = `luvhive_followers_${targetUser.username}`;
      let followers = [];
      
      const existingFollowers = localStorage.getItem(followersKey);
      if (existingFollowers) {
        followers = JSON.parse(existingFollowers);
      }

      if (isFollowing) {
        // Remove from followers
        followers = followers.filter(username => username !== currentUser.username);
      } else {
        // Add to followers
        if (!followers.includes(currentUser.username)) {
          followers.push(currentUser.username);
        }
      }

      localStorage.setItem(followersKey, JSON.stringify(followers));

      setIsFollowing(!isFollowing);

      // Show success message
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert(
          isFollowing 
            ? `You unfollowed ${targetUser.name}` 
            : `You're now following ${targetUser.name}! ✨`
        );
      }

    } catch (error) {
      console.error('Error updating follow status:', error);
    }

    setIsLoading(false);
  };

  const handleMessage = () => {
    try {
      if (window.Telegram?.WebApp) {
        // Redirect to premium bot features
        showAlert(
          `💬 Want to chat with ${targetUser.name}?\n\n` +
          "🔥 Premium Chat Features:\n" +
          "• Gender-based matching\n" +
          "• Random chat with filters\n" +
          "• Advanced matching options\n\n" +
          "💎 Upgrade to Premium in the bot for unlimited chatting!"
        );
        
        // Optional: Close the modal and return to bot after showing alert
        setTimeout(() => {
          closeTelegramWebApp();
        }, 4000);
      } else {
        // Fallback for non-Telegram environments
        alert("Premium chat features available in the LuvHive bot! 💎");
        // Try to open Telegram bot
        const botUrl = 'https://t.me/LuvHiveBot';
        window.open(botUrl, '_blank');
      }
    } catch (error) {
      console.error('Error in handleMessage:', error);
      alert("Unable to open premium chat. Please visit the LuvHive bot directly.");
    }
  };

  const handleSendSpark = async () => {
    try {
      // Simulate sending spark with loading state
      const button = document.querySelector('[data-spark-btn]');
      if (button) {
        button.disabled = true;
        button.innerHTML = '⏳ Sending...';
      }

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Save spark to localStorage (simulate backend)
      const sparkKey = `luvhive_sparks_sent_${currentUser?.username}`;
      const existingSparks = JSON.parse(localStorage.getItem(sparkKey) || '[]');
      const newSpark = {
        id: Date.now(),
        targetUser: targetUser.username,
        timestamp: new Date().toISOString(),
        status: 'sent'
      };
      
      if (!existingSparks.find(spark => spark.targetUser === targetUser.username)) {
        existingSparks.push(newSpark);
        localStorage.setItem(sparkKey, JSON.stringify(existingSparks));
      }

      // Enhanced spark interaction instead of direct message
      showAlert(
        `✨ Spark sent to ${targetUser.name}!\n\n` +
        "They'll be notified that you're interested in connecting. " +
        "If they spark you back, you'll both get a notification! 💫"
      );

      // Reset button
      if (button) {
        button.innerHTML = '✨ Spark Sent!';
        button.className = button.className.replace('from-yellow-400 to-orange-500', 'from-green-400 to-green-600');
        setTimeout(() => {
          button.innerHTML = '<span class="mr-2">✨</span>Send Spark';
          button.className = button.className.replace('from-green-400 to-green-600', 'from-yellow-400 to-orange-500');
          button.disabled = false;
        }, 2000);
      }
    } catch (error) {
      console.error('Error sending spark:', error);
      showAlert("❌ Error sending spark. Please try again!");
      
      // Reset button on error
      const button = document.querySelector('[data-spark-btn]');
      if (button) {
        button.innerHTML = '<span class="mr-2">✨</span>Send Spark';
        button.disabled = false;
      }
    }
  };

  if (!targetUser) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/90 flex items-end sm:items-center justify-center z-50">
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full sm:max-w-md mx-4 max-h-[95vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold">@{targetUser.username}</h2>
          <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(95vh-80px)]">
          {/* Profile Header */}
          <div className="p-6">
            <div className="flex items-center space-x-4 mb-6">
              {/* Profile Picture */}
              <div className="w-20 h-20 rounded-full overflow-hidden bg-gradient-to-r from-purple-400 to-pink-500 flex-shrink-0">
                <img 
                  src={targetUser.profilePic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${targetUser.name}`} 
                  alt={targetUser.name} 
                  className="w-full h-full object-cover" 
                />
              </div>

              {/* Stats */}
              <div className="flex-1 grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xl font-bold text-gray-800">{userPosts.length}</div>
                  <div className="text-sm text-gray-500">Posts</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-gray-800">{followerCount}</div>
                  <div className="text-sm text-gray-500">Followers</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-gray-800">{Math.floor(Math.random() * 300) + 50}</div>
                  <div className="text-sm text-gray-500">Following</div>
                </div>
              </div>
            </div>

            {/* Name & Bio */}
            <div className="mb-6">
              <h3 className="text-lg font-bold text-gray-800 mb-1">{targetUser.name}</h3>
              {targetUser.bio && (
                <p className="text-gray-600 leading-relaxed">{targetUser.bio}</p>
              )}
              
              {/* Mood & Aura */}
              <div className="flex items-center space-x-4 mt-3">
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center">
                    <span className="text-sm">🧠</span>
                  </div>
                  <span className="text-sm text-purple-600 capitalize">{targetUser.mood || 'happy'}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center">
                    <span className="text-sm">🌌</span>
                  </div>
                  <span className="text-sm text-indigo-600 capitalize">{targetUser.aura || 'golden'}</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            {currentUser && targetUser.username !== currentUser.username && (
              <div className="grid grid-cols-2 gap-3 mb-6">
                {/* Follow/Unfollow Button */}
                <button
                  onClick={handleFollowToggle}
                  disabled={isLoading}
                  className={`col-span-2 py-3 rounded-2xl font-semibold transition-all duration-200 ${
                    isFollowing
                      ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      : 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg transform hover:scale-105'
                  }`}
                >
                  {isLoading ? '⏳' : isFollowing ? 'Following ✓' : 'Follow'}
                </button>

                {/* Spark Button - Alternative to messaging */}
                <button
                  data-spark-btn
                  onClick={handleSendSpark}
                  className="flex items-center justify-center py-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-white rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                >
                  <span className="mr-2">✨</span>
                  Send Spark
                </button>

                {/* Premium Chat Redirect */}
                <button
                  onClick={handleMessage}
                  className="flex items-center justify-center py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                >
                  <span className="mr-2">💎</span>
                  Premium Chat
                </button>
              </div>
            )}

            {/* Vibe Score */}
            {currentUser && targetUser.username !== currentUser.username && (
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl p-4 mb-6">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-800">Vibe Compatibility</span>
                  <span className="text-lg font-bold text-purple-600">{Math.floor(Math.random() * 30) + 70}%</span>
                </div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.floor(Math.random() * 30) + 70}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>

          {/* Posts Grid */}
          <div className="border-t border-gray-100">
            <div className="p-4">
              <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                <span className="mr-2">📸</span>
                Recent Posts
              </h4>
              
              {userPosts.length > 0 ? (
                <div className="grid grid-cols-3 gap-2">
                  {userPosts.map((post) => (
                    <div key={post.id} className="relative aspect-square">
                      <img 
                        src={post.image} 
                        alt="Post" 
                        className="w-full h-full object-cover rounded-xl hover:opacity-90 transition-opacity cursor-pointer"
                      />
                      <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded-full">
                        ✨{post.likes}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">📷</div>
                  <p>No posts yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ViewUserProfile;