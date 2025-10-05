import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CreatePost from './CreatePost';
import Stories from './Stories';
import CreateStory from './CreateStory';
import TabExplanation from './TabExplanation';
import ViewUserProfile from './ViewUserProfile';
import PostOptionsModal from './PostOptionsModal';
import ShareModal from './ShareModal';
import ReplyModal from './ReplyModal';
import CommentsModal from './CommentsModal';
import Avatar from './ui/Avatar';

// Helper function to format time in IST
const formatTimeIST = (timestamp) => {
  try {
    const now = new Date();
    const postTime = new Date(timestamp);
    
    // If invalid date, return fallback
    if (isNaN(postTime.getTime())) {
      return 'just now';
    }
    
    const diffMs = now - postTime;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMinutes < 1) {
      return 'just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return `${diffDays}d ago`;
    }
  } catch (error) {
    console.error('Time formatting error:', error);
    return 'just now';
  }
};

// Mock posts data outside component to avoid dependency issues
const mockPostsData = [
  {
    id: 'user_post_1',
    user: { 
      name: 'Test User', 
      username: 'testuser', 
      avatarUrl: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=center',
      profilePic: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=center'
    },
    content: 'Just joined LuvHive! Excited to connect with amazing people 🚀✨',
    image: null,
    mood: 'excited',
    vibeScore: 95,
    sparkCount: 12,
    glowCount: 8,
    userReactions: { spark: false, glow: false },
    timestamp: '2h ago',
    createdAt: new Date(Date.now() - 14 * 60 * 60 * 1000).toISOString(), // 14 hours ago
    isSparkPost: false,
    comments: [],
    comments_count: 0
  },
  {
    id: 0,
    user: { 
      name: 'Luvsociety', 
      username: '@luvsociety', 
      avatarUrl: 'https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=200&h=200&fit=crop&crop=center',
      profilePic: 'https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=200&h=200&fit=crop&crop=center'
    },
    content: 'So yummy 😋',
    image: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop&crop=center',
    mood: 'happy',
    vibeScore: 88,
    sparkCount: 0,
    glowCount: 1,
    userReactions: { spark: false, glow: false },
    timestamp: '30m ago',
    createdAt: new Date(Date.now() - 15 * 60 * 60 * 1000).toISOString(), // 15 hours ago
    isSparkPost: false,
    comments: [
      {
        id: 1,
        user: { name: 'Alex Dream', username: '@alex_cosmic', avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=center', profilePic: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=center' },
        text: 'Looks delicious! 🤤',
        timestamp: '2m ago',
        likes: 2
      },
      {
        id: 2,
        user: { name: 'Emma Soul', username: '@emma_vibes', avatarUrl: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=center', profilePic: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=center' },
        text: 'Nature always has the best surprises! 🌿✨',
        timestamp: '1h ago',
        likes: 3
      }
    ],
    comments_count: 2
  },
  {
    id: 1,
    user: { 
      name: 'Emma Soul', 
      username: '@emma_vibes', 
      avatarUrl: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=center',
      profilePic: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=center'
    },
    content: 'Just discovered this hidden waterfall during my morning hike! Sometimes the best adventures are unplanned 🏞️✨',
    image: 'https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=400',
    mood: 'adventurous',
    vibeScore: 92,
    sparkCount: 47,
    glowCount: 23,
    userReactions: { spark: false, glow: false },
    timestamp: '3h ago',
    createdAt: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(), // 18 hours ago
    isSparkPost: false,
    comments: [
      {
        id: 1,
        user: { name: 'Alex Dream', username: '@alex_cosmic', avatarUrl: 'https://ui-avatars.com/api/?name=Alex+Dream&background=8b5cf6&color=fff&size=200' },
        text: 'Wow, that looks amazing! 😍 Where is this place?',
        timestamp: '2h ago',
        likes: 5
      },
      {
        id: 2,
        user: { name: 'Zara Wild', username: '@zara_free', avatarUrl: 'https://ui-avatars.com/api/?name=Zara+Wild&background=ec4899&color=fff&size=200' },
        text: 'Nature always has the best surprises! 🌿✨',
        timestamp: '1h ago',
        likes: 3
      }
    ],
    comments_count: 2
  },
  {
    id: 2,
    user: { 
      name: 'Alex Dream', 
      username: '@alex_cosmic', 
      avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=center',
      profilePic: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=center'
    },
    content: 'Tonight\'s meditation brought me such clarity. We\'re all stardust experiencing itself subjectively 🌌',
    mood: 'philosophical',
    vibeScore: 88,
    sparkCount: 34,
    glowCount: 19,
    userReactions: { spark: false, glow: false },
    timestamp: '5h ago',
    createdAt: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(), // 20 hours ago
    isSparkPost: true,
    sparkDuration: '18h remaining'
  },
  {
    id: 3,
    user: { 
      name: 'Zara Wild', 
      username: '@zara_free', 
      avatarUrl: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=200&h=200&fit=crop&crop=center',
      profilePic: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=200&h=200&fit=crop&crop=center'
    },
    content: 'Dancing in my kitchen to 90s music because life is too short not to be silly sometimes! 💃',
    video: true,
    mood: 'playful',
    vibeScore: 95,
    sparkCount: 67,
    glowCount: 41,
    userReactions: { spark: false, glow: false },
    timestamp: '1d ago',
    createdAt: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(), // 1.5 days ago
    isSparkPost: false
  }
];

const SocialFeed = ({ user, theme }) => {
  const navigate = useNavigate();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('following');
  const [showCreatePost, setShowCreatePost] = useState(false);
  const [showStories, setShowStories] = useState(false);
  const [showCreateStory, setShowCreateStory] = useState(false);
  const [stories, setStories] = useState([]);
  const [showTabExplanation, setShowTabExplanation] = useState(false);
  const [selectedTab, setSelectedTab] = useState('following');
  const [showViewProfile, setShowViewProfile] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showPostOptions, setShowPostOptions] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [showReplyModal, setShowReplyModal] = useState(false);
  const [showCommentsModal, setShowCommentsModal] = useState(false);
  const [selectedPost, setSelectedPost] = useState(null);
  const [fullScreenImage, setFullScreenImage] = useState(null);

  // Get user stories and mock stories
  const getMockStories = () => {
    // Create a default user if none exists
    const defaultUser = user || { name: 'Test User', username: 'testuser', profilePic: '✨' };
    
    // Check if user has stories in localStorage
    const userStoriesKey = `luvhive_stories_${defaultUser.username}`;
    const userStories = JSON.parse(localStorage.getItem(userStoriesKey) || '[]');
    const hasUserStories = userStories.length > 0;
    
    return [
      {
        id: 1,
        user: { 
          name: 'Your Story', 
          username: defaultUser.username, 
          avatar: defaultUser.profilePic || '✨', 
          isOwn: true 
        },
        hasStories: hasUserStories,
        stories: userStories
      },
      {
        id: 2,
        user: { name: 'Luna Starlight', username: 'luna_cosmic', avatar: '🌙' },
        hasStories: true
      },
      {
        id: 3,
        user: { name: 'River Phoenix', username: 'river_wild', avatar: '🌊' },
        hasStories: true
      },
      {
        id: 4,
        user: { name: 'Nova Bright', username: 'nova_shine', avatar: '⭐' },
        hasStories: true
      }
    ];
  };

  useEffect(() => {
    const loadPosts = () => {
      try {
        // Create default user for fallback
        const defaultUser = user || { name: 'Test User', username: 'testuser', profilePic: '✨' };
        
        // Load user's own posts from localStorage
        let userPosts = [];
        const userPostsKey = `luvhive_posts_${defaultUser.username}`;
        userPosts = JSON.parse(localStorage.getItem(userPostsKey) || '[]');
        
        // Combine with mock posts
        const allPosts = [...userPosts, ...mockPostsData];
        
        // Merge currentUser avatar with posts user - CLIENT-SIDE FIX
        const postsWithUpdatedAvatars = allPosts.map(p => {
          // If this post belongs to current user, update avatar from current user data
          if (user && (
            p.user.id === user.id || 
            p.user.username === user.username || 
            p.user.name === user.name ||
            p.user.username === 'testuser' || 
            p.user.name === 'Test User'
          )) {
            return {
              ...p,
              user: {
                ...p.user,
                avatarUrl: user.avatarUrl || user.profilePic || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=center'
              }
            };
          }
          return p;
        });
        
        console.log('📄 Loaded posts with updated avatars:', postsWithUpdatedAvatars.length);
        setPosts(postsWithUpdatedAvatars);
        setStories(getMockStories());
        setLoading(false); // Important: Set loading to false
      } catch (error) {
        console.error('❌ Error loading posts:', error);
        setPosts(mockPostsData);
        setStories(getMockStories());
        setLoading(false); // Important: Set loading to false even on error
      }
    };
    
    loadPosts();
  }, []); // Remove dependencies to prevent infinite loops

  const handlePostCreated = (newPost) => {
    setPosts(prev => [newPost, ...prev]);
  };

  const handleCreateStory = (newStory) => {
    console.log('📖 handleCreateStory called with:', newStory);
    // Force immediate refresh by recreating the stories array
    setTimeout(() => {
      const refreshedStories = getMockStories();
      setStories(refreshedStories);
      console.log('📖 Stories updated after delay:', refreshedStories);
    }, 100);
  };

  const handleNewPost = (newPost) => {
    console.log('📝 handleNewPost called with:', newPost);
    // Add new post to the beginning of the current posts list
    setPosts(prev => [newPost, ...prev]);
    console.log('📝 Posts updated - new post added to feed');
  };

  const handleUserClick = (postUser) => {
    // Don't show profile for current user
    if (user && postUser.name === user.name) {
      navigate('/profile');
      return;
    }
    
    // Show other user's profile
    setSelectedUser(postUser);
    setShowViewProfile(true);
  };

  const openReplyModal = (postId) => {
    const post = posts.find(p => p.id === postId);
    if (post) {
      setSelectedPost(post);
      setShowReplyModal(true);
    }
  };

  const handleDeletePost = async (postId) => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const response = await fetch(`${backendUrl}/api/posts/${postId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          // Include Telegram WebApp initData for authentication if available
          ...(window.Telegram?.WebApp?.initData ? {
            'X-Telegram-Init-Data': window.Telegram.WebApp.initData
          } : {})
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'पोस्ट डिलीट नहीं हो सकी।');
      }

      const result = await response.json();
      
      if (result.success) {
        // Remove post from frontend state
        setPosts(prevPosts => prevPosts.filter(p => p.id !== postId));
        
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert("🗑️ पोस्ट सफलतापूर्वक डिलीट हो गई!");
        } else {
          alert("🗑️ पोस्ट सफलतापूर्वक डिलीट हो गई!");
        }
      } else {
        throw new Error(result.message || 'पोस्ट डिलीट नहीं हो सकी।');
      }
    } catch (error) {
      console.error('❌ Delete post error:', error);
      const errorMsg = error.message || 'पोस्ट डिलीट करने में त्रुटि हुई।';
      
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert(`❌ ${errorMsg}`);
      } else {
        alert(`❌ ${errorMsg}`);
      }
    }
  };

  const handleShare = (postId) => {
    const post = posts.find(p => p.id === postId);
    if (post) {
      setSelectedPost(post);
      setShowShareModal(true);
    }
  };

  const handlePostMenu = (post) => {
    console.log('3-dot menu clicked for post:', post.id);
    setSelectedPost(post);
    setShowPostOptions(true);
  };

  const handlePostAction = async (actionId, post) => {
    if (actionId === 'delete') {
      // Confirmation dialog
      const confirmMessage = "Are you sure you want to delete this post?";
      
      // eslint-disable-next-line no-restricted-globals
      const confirmed = confirm(confirmMessage);
      
      if (confirmed) {
        try {
          // Remove post from state
          setPosts(posts => posts.filter(p => p.id !== post.id));
          alert('Post deleted successfully!');
        } catch (error) {
          console.error('Delete error:', error);
          alert('Failed to delete post: ' + error.message);
        }
      }
      return;
    }
    
    switch (actionId) {
      // handle other actions...
      default:
        const actions = {
          report: async () => {
            if (window.Telegram?.WebApp?.showAlert) {
              window.Telegram.WebApp.showAlert("🚨 Post reported! Our team will review it. Thank you for keeping LuvHive safe.");
            } else {
              alert("Post reported successfully!");
            }
          },
          save: async () => {
            // Save post to localStorage
            const savedPosts = JSON.parse(localStorage.getItem(`luvhive_saved_${user?.username}`) || '[]');
            if (!savedPosts.find(p => p.id === post.id)) {
              savedPosts.push(post);
              localStorage.setItem(`luvhive_saved_${user?.username}`, JSON.stringify(savedPosts));
            }
            
            if (window.Telegram?.WebApp?.showAlert) {
              window.Telegram.WebApp.showAlert("💾 Post saved! Check your saved posts in profile.");
            } else {
              alert("Post saved!");
            }
          },
          hide: async () => {
            // Hide post from feed
            setPosts(prevPosts => prevPosts.filter(p => p.id !== post.id));
            
            if (window.Telegram?.WebApp?.showAlert) {
              window.Telegram.WebApp.showAlert("🙈 Post hidden from your feed.");
            } else {
              alert("Post hidden!");
            }
          },
          copy: async () => {
            const postUrl = `${window.location.origin}/post/${post.id}`;
            try {
              await navigator.clipboard.writeText(postUrl);
              if (window.Telegram?.WebApp?.showAlert) {
                window.Telegram.WebApp.showAlert("🔗 Link copied to clipboard!");
              } else {
                alert("Link copied!");
              }
            } catch (error) {
              console.error('Failed to copy link:', error);
            }
          },
          block: async () => {
            const isOwnPost = user && (post.user.name === user.name || post.user.username === user.username);
            
            if (isOwnPost) {
              // If it's own post, redirect to delete
              await actions.delete();
              return;
            }
            
            // Block user logic
            const confirmMessage = `क्या आप ${post.user.name} को ब्लॉक करना चाहते हैं?`;
            
            if (window.Telegram?.WebApp?.showConfirm) {
              window.Telegram.WebApp.showConfirm(
                confirmMessage,
                (confirmed) => {
                  if (confirmed) {
                    setPosts(prevPosts => prevPosts.filter(p => p.user.name !== post.user.name));
                    if (window.Telegram?.WebApp?.showAlert) {
                      window.Telegram.WebApp.showAlert(`🚫 ${post.user.name} को ब्लॉक कर दिया गया।`);
                    } else {
                      alert(`${post.user.name} को ब्लॉक कर दिया गया।`);
                    }
                  }
                }
              );
            } else {
              // eslint-disable-next-line no-restricted-globals
              if (confirm(confirmMessage)) {
                setPosts(prevPosts => prevPosts.filter(p => p.user.name !== post.user.name));
                alert(`${post.user.name} को ब्लॉक कर दिया गया।`);
              }
            }
          }
        };

        const action = actions[actionId];
        if (action) {
          await action();
        }
    }
  };

  const tabs = [
    { id: 'following', label: 'Following', icon: '💕', shortLabel: 'Follow' },
    { id: 'discover', label: 'Discover', icon: '🔮', shortLabel: 'Find' },
    { id: 'vibes', label: 'Vibes', icon: '🌈', shortLabel: 'Vibes' },
    { id: 'sparks', label: 'Sparks', icon: '✨', shortLabel: 'Spark' }
  ];

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    
    // For Telegram WebApp, we can show helpful explanations
    if (window.Telegram?.WebApp && tabId !== 'following') {
      setSelectedTab(tabId);
      setShowTabExplanation(true);
    }
  };

  const handleCreatePost = () => {
    console.log('Create post button clicked - setting showCreatePost to true');
    setShowCreatePost(true);
    console.log('showCreatePost state should now be true');
  };

  const handleSpark = (postId) => {
    setPosts(posts.map(post => {
      if (post.id === postId) {
        const hasUserSparked = post.userReactions?.spark || false;
        const hasUserGlowed = post.userReactions?.glow || false;
        
        // If user already glowed, remove glow and add spark
        if (hasUserGlowed) {
          return { 
            ...post, 
            sparkCount: (post.sparkCount || 0) + 1,
            glowCount: Math.max((post.glowCount || 0) - 1, 0),
            userReactions: { spark: true, glow: false }
          };
        }
        // If user already sparked, remove spark
        else if (hasUserSparked) {
          return { 
            ...post, 
            sparkCount: Math.max((post.sparkCount || 0) - 1, 0),
            userReactions: { ...post.userReactions, spark: false }
          };
        }
        // First time spark
        else {
          return { 
            ...post, 
            sparkCount: (post.sparkCount || 0) + 1,
            userReactions: { ...post.userReactions, spark: true }
          };
        }
      }
      return post;
    }));
  };

  const handleGlow = (postId) => {
    setPosts(posts.map(post => {
      if (post.id === postId) {
        const hasUserSparked = post.userReactions?.spark || false;
        const hasUserGlowed = post.userReactions?.glow || false;
        
        // If user already sparked, remove spark and add glow
        if (hasUserSparked) {
          return { 
            ...post, 
            glowCount: (post.glowCount || 0) + 1,
            sparkCount: Math.max((post.sparkCount || 0) - 1, 0),
            userReactions: { spark: false, glow: true }
          };
        }
        // If user already glowed, remove glow
        else if (hasUserGlowed) {
          return { 
            ...post, 
            glowCount: Math.max((post.glowCount || 0) - 1, 0),
            userReactions: { ...post.userReactions, glow: false }
          };
        }
        // First time glow
        else {
          return { 
            ...post, 
            glowCount: (post.glowCount || 0) + 1,
            userReactions: { ...post.userReactions, glow: true }
          };
        }
      }
      return post;
    }));
  };

  const handleReply = async (postId, reply) => {
    try {
      const token = window.Telegram?.WebApp?.initData || localStorage.getItem('authToken') || '';
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/posts/${postId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text: reply.text })
      });
      setPosts(posts => posts.map(p => p._id === postId || p.id === postId ? { ...p, replies: [...(p.replies || []), reply] } : p));
    } catch (error) {
      console.error('Error adding reply:', error);
    }
  };

  const handleAddComment = async (comment) => {
    try {
      // Save comment to backend
      const token = window.Telegram?.WebApp?.initData || localStorage.getItem('authToken') || '';
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/posts/${selectedPost.id || selectedPost._id}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text: comment.text })
      });
      
      // Update local state
      setPosts(posts => posts.map(post =>
        (post.id === selectedPost.id || post._id === selectedPost._id) ? { 
          ...post, 
          comments: [...(post.comments || []), comment],
          comments_count: (post.comments_count || 0) + 1
        } : post
      ));
    } catch (error) {
      console.error('Error adding comment:', error);
    }
  };

  // Function to sync user profile updates across posts
  const updateUserAvatarInPosts = (userId, newAvatarUrl) => {
    setPosts(posts.map(p => 
      p.user.id === userId || p.user.username === userId || p.user.name === userId
        ? { ...p, user: { ...p.user, avatarUrl: newAvatarUrl } }
        : p
    ));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-4 animate-pulse-love mx-auto">
            <span className="text-2xl animate-heart-beat">💫</span>
          </div>
          <p className="text-white text-lg font-medium">Syncing your vibes...</p>
          <div className="mt-4 flex justify-center space-x-1">
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce delay-100"></div>
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce delay-200"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-purple-50">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-white/90 backdrop-blur-lg shadow-sm border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 rounded-full hover:bg-gray-100 transition-all duration-200"
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <div className="flex items-center space-x-2">
            <div className="animate-heart-beat">💕</div>
            <h1 className="text-xl font-bold text-gray-800">LuvHive</h1>
          </div>
          
          <button
            onClick={() => navigate('/instagram-profile')}
            className="w-8 h-8 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full flex items-center justify-center"
            title="My Profile"
          >
            <span className="text-white text-sm">👤</span>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`flex-1 py-3 px-1 text-center relative transition-all duration-200 ${
                activeTab === tab.id
                  ? 'text-purple-600 font-semibold'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center justify-center space-x-1">
                <span className="text-sm">{tab.icon}</span>
                <span className="text-xs sm:text-sm hidden sm:inline">{tab.label}</span>
                <span className="text-xs sm:hidden">{tab.shortLabel}</span>
                {/* Info icon for non-Following tabs */}
                {tab.id !== 'following' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedTab(tab.id);
                      setShowTabExplanation(true);
                    }}
                    className="ml-1 text-xs text-gray-400 hover:text-purple-500"
                  >
                    ℹ️
                  </button>
                )}
              </div>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full"></div>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 py-6 space-y-6">
        {/* Stories Section */}
        <div className="flex space-x-3 overflow-x-auto pb-2">
          {stories.map((story, index) => (
            <button
              key={story.id}
              onClick={() => {
                console.log('Story clicked:', story.user.name, 'isOwn:', story.user.isOwn, 'hasStories:', story.hasStories);
                if (story.user.isOwn) {
                  // For own story - always create new story when + button clicked
                  console.log('Creating new story');
                  setShowCreateStory(true);
                } else {
                  // Show other user's stories
                  console.log('Opening other user stories');
                  setSelectedUser(story.user);
                  setShowStories(true);
                }
              }}
              className="flex-shrink-0 text-center"
            >
              <div className={`w-16 h-16 rounded-full p-0.5 ${
                story.user.isOwn 
                  ? (story.hasStories 
                      ? 'bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500'
                      : 'bg-gradient-to-r from-gray-300 to-gray-400')
                  : 'bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500'
              }`}>
                <div className="w-full h-full rounded-full overflow-hidden bg-white">
                  {story.user.isOwn ? (
                    <div className="w-full h-full bg-gradient-to-r from-pink-500 to-purple-600 flex items-center justify-center relative">
                      {story.hasStories ? (
                        <>
                          {/* Show latest story preview */}
                          <span className="text-2xl">🌟</span>
                          <div className="absolute bottom-0 right-0 w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center">
                            +
                          </div>
                        </>
                      ) : (
                        <>
                          <span className="text-2xl">✨</span>
                          <div className="absolute bottom-0 right-0 w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center">
                            +
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="w-full h-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center">
                      <span className="text-2xl">{story.user.avatar}</span>
                    </div>
                  )}
                </div>
              </div>
              <p className="text-xs text-gray-600 mt-1 max-w-[64px] truncate">
                {story.user.isOwn ? 'Your Story' : story.user.name.split(' ')[0]}
              </p>
            </button>
          ))}
        </div>

        {/* Create Post Button */}
        <button
          onClick={handleCreatePost}
          className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white py-4 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center justify-center space-x-2"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>Share Your Vibe</span>
        </button>

        {/* Posts */}
        {posts.map(post => (
          <div key={post.id} className="bg-white rounded-3xl shadow-lg overflow-hidden">
            {/* Post Header */}
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <div 
                  className="flex items-center space-x-3 cursor-pointer hover:bg-gray-50 rounded-2xl p-2 -m-2 transition-colors"
                  onClick={() => handleUserClick(post.user)}
                >
                  <Avatar user={post.user} size={48} />
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="font-semibold text-gray-800 hover:text-purple-600 transition-colors">
                        {post.user.name}
                      </h3>
                      <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                        post.user.mood === 'joyful' ? 'bg-yellow-100 text-yellow-800' :
                        post.user.mood === 'contemplative' ? 'bg-purple-100 text-purple-800' :
                        post.user.mood === 'energetic' ? 'bg-pink-100 text-pink-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {post.user.mood}
                      </div>
                    </div>
                    <p className="text-sm text-gray-500">{post.user.username} • {post.createdAt ? formatTimeIST(post.createdAt) : post.timestamp}</p>
                  </div>
                </div>
                
                {post.isSparkPost && (
                  <div className="flex items-center space-x-1 bg-gradient-to-r from-yellow-100 to-orange-100 px-2 py-1 rounded-full">
                    <span className="text-xs">✨</span>
                    <span className="text-xs text-orange-600 font-medium">{post.sparkDuration}</span>
                  </div>
                )}

                {/* Post Menu Button */}
                <button
                  onClick={() => handlePostMenu(post)}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors ml-2"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                  </svg>
                </button>
              </div>
              
              {/* Vibe Score */}
              <div className="mt-3 flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                  <div 
                    className={`h-full rounded-full bg-gradient-to-r ${
                      post.vibeScore >= 90 ? 'from-green-400 to-emerald-500' :
                      post.vibeScore >= 80 ? 'from-yellow-400 to-orange-500' :
                      'from-pink-400 to-purple-500'
                    }`}
                    style={{ width: `${post.vibeScore}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-500 font-medium">{post.vibeScore}% vibe</span>
              </div>
            </div>

            {/* Post Content */}
            <div className="p-4">
              <p className="text-gray-800 leading-relaxed mb-3">{post.content}</p>
              
              {/* Render media array (images and videos) */}
              {post.images && post.images.length > 0 && (
                <div className={`grid gap-2 mb-3 ${post.images.length === 1 ? 'grid-cols-1' : post.images.length === 2 ? 'grid-cols-2' : 'grid-cols-2'}`}>
                  {post.images.slice(0, 4).map((mediaUrl, idx) => {
                    // Detect if this is a video URL (basic check)
                    const isVideo = mediaUrl.includes('video') || mediaUrl.includes('.mp4') || mediaUrl.includes('.mov') || mediaUrl.includes('.webm');
                    
                    return (
                      <div key={idx} className="rounded-2xl overflow-hidden relative">
                        {isVideo ? (
                          <video 
                            src={mediaUrl} 
                            className="w-full h-64 object-cover cursor-pointer"
                            controls
                            preload="metadata"
                            poster={mediaUrl.replace('video', 'thumb')} // Try to get thumbnail
                            onClick={() => setFullScreenImage({ url: mediaUrl, alt: `${post.user.name}'s video`, isVideo: true })}
                          />
                        ) : (
                          <img 
                            src={mediaUrl} 
                            alt={`Post media ${idx + 1}`} 
                            className="w-full h-64 object-cover cursor-pointer hover:opacity-90 transition-opacity" 
                            onClick={() => setFullScreenImage({ url: mediaUrl, alt: `${post.user.name}'s photo` })}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              
              {/* Fallback for old single image format */}
              {!post.images && post.image && (
                <div className="rounded-2xl overflow-hidden mb-3">
                  <img 
                    src={post.image} 
                    alt="Post content" 
                    className="w-full h-64 object-cover cursor-pointer hover:opacity-90 transition-opacity" 
                    onClick={() => setFullScreenImage({ url: post.image, alt: `${post.user.name}'s photo` })}
                    onError={(e) => {
                      // Hide broken image
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              )}
              
              {/* Fallback for old video format */}
              {post.video && (
                <div className="rounded-2xl overflow-hidden mb-3">
                  <video 
                    src={post.video} 
                    className="w-full h-64 object-cover cursor-pointer"
                    controls
                    preload="metadata"
                    onClick={() => setFullScreenImage({ url: post.video, alt: `${post.user.name}'s video`, isVideo: true })}
                  />
                </div>
              )}
            </div>

            {/* Post Actions */}
            <div className="px-4 pb-4">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => handleSpark(post.id)}
                  className={`flex items-center space-x-1 px-3 py-2 rounded-full hover:shadow-lg transform hover:scale-105 transition-all duration-200 ${
                    post.userReactions?.spark 
                      ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-white shadow-lg scale-105' 
                      : 'bg-gray-100 hover:bg-yellow-100 text-yellow-600 hover:text-yellow-700'
                  }`}
                >
                  <span>✨</span>
                  <span className="text-sm font-medium">{post.sparkCount || 0}</span>
                </button>
                
                <button
                  onClick={() => handleGlow(post.id)}
                  className={`flex items-center space-x-1 px-3 py-2 rounded-full hover:shadow-lg transform hover:scale-105 transition-all duration-200 ${
                    post.userReactions?.glow 
                      ? 'bg-gradient-to-r from-pink-400 to-purple-500 text-white shadow-lg scale-105' 
                      : 'bg-gray-100 hover:bg-pink-100 text-pink-600 hover:text-pink-700'
                  }`}
                >
                  <span>💫</span>
                  <span className="text-sm font-medium">{post.glowCount || 0}</span>
                </button>
                
                <button
                  onClick={() => {
                    setSelectedPost(post);
                    setShowCommentsModal(true);
                  }}
                  className="flex items-center space-x-1 bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-2 rounded-full transition-all duration-200"
                >
                  <span>💬</span>
                  <span className="text-sm font-medium">
                    Comments {post.comments?.length ? `(${post.comments.length})` : ''}
                  </span>
                </button>
                
                <button 
                  onClick={() => handleShare(post.id)}
                  className="flex items-center space-x-1 bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-2 rounded-full transition-all duration-200"
                >
                  <span>🔗</span>
                  <span className="text-sm font-medium">Share</span>
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* Load More */}
        <div className="text-center py-6">
          <button className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-full font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200">
            Load More Vibes ✨
          </button>
        </div>
      </div>

      {/* Modals */}
      {/* Removed duplicate CreatePost modal */}

      {showStories && (
        <Stories
          user={user}
          targetUser={selectedUser}
          onClose={() => {
            setShowStories(false);
            setSelectedUser(null);
          }}
        />
      )}

      {showCreateStory && (
        <CreateStory
          user={user || { name: 'Test User', username: 'testuser', profilePic: '🌟' }}
          onClose={() => setShowCreateStory(false)}
          onStoryCreated={handleCreateStory}
        />
      )}

      {showTabExplanation && (
        <TabExplanation
          activeTab={selectedTab}
          onClose={() => setShowTabExplanation(false)}
        />
      )}

      {showViewProfile && selectedUser && (
        <ViewUserProfile
          targetUser={selectedUser}
          currentUser={user}
          onClose={() => setShowViewProfile(false)}
        />
      )}

      {showPostOptions && selectedPost && (
        <PostOptionsModal
          post={selectedPost}
          currentUser={user}
          onClose={() => {
            setShowPostOptions(false);
            setSelectedPost(null);
          }}
          onAction={handlePostAction}
        />
      )}

      {showShareModal && selectedPost && (
        <ShareModal
          post={selectedPost}
          currentUser={user}
          onClose={() => {
            setShowShareModal(false);
            setSelectedPost(null);
          }}
        />
      )}

      {/* Full Screen Image Modal */}
      {fullScreenImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4"
          onClick={() => setFullScreenImage(null)}
        >
          <div className="relative max-w-4xl max-h-full">
            <button
              onClick={() => setFullScreenImage(null)}
              className="absolute top-4 right-4 text-white bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full p-2 z-10 transition-all"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            {fullScreenImage.isVideo ? (
              <video
                src={fullScreenImage.url}
                className="max-w-full max-h-full object-contain rounded-lg"
                controls
                autoPlay
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <img
                src={fullScreenImage.url}
                alt={fullScreenImage.alt}
                className="max-w-full max-h-full object-contain rounded-lg"
                onClick={(e) => e.stopPropagation()}
              />
            )}
          </div>
        </div>
      )}

      {showReplyModal && selectedPost && (
        <ReplyModal
          post={selectedPost}
          currentUser={user}
          onReply={reply => handleReply(selectedPost._id || selectedPost.id, reply)}
          onClose={() => {
            setShowReplyModal(false);
            setSelectedPost(null);
          }}
        />
      )}

      {showCommentsModal && selectedPost && (
        <CommentsModal
          post={selectedPost}
          currentUser={user}
          onClose={() => {
            setShowCommentsModal(false);
            setSelectedPost(null);
          }}
          onAddComment={handleAddComment}
        />
      )}

      {showCreatePost && (
        <CreatePost
          user={user || { name: 'Test User', username: 'testuser', profilePic: '🌟' }}
          onClose={() => setShowCreatePost(false)}
          onPostCreated={handleNewPost}
        />
      )}
    </div>
  );
};

export default SocialFeed;