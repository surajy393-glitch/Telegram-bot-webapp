import React, { useState, useEffect } from 'react';

const Settings = ({ user, onClose, onSettingsUpdate }) => {
  const [settings, setSettings] = useState({
    isPublic: true,
    allowMessages: true,
    showOnlineStatus: true,
    allowTagging: true,
    showInSearch: true,
    allowStoryReplies: true,
    pushNotifications: true,
    emailNotifications: false,
    showVibeScore: true,
    allowLocationSharing: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const savedSettings = localStorage.getItem(`luvhive_settings_${user.username}`);
    if (savedSettings) {
      try {
        setSettings(JSON.parse(savedSettings));
      } catch (error) {
        console.error('Error loading settings:', error);
      }
    }
  }, [user.username]);

  const handleToggle = (settingKey) => {
    setSettings(prev => ({
      ...prev,
      [settingKey]: !prev[settingKey]
    }));
  };

  const handleSave = async () => {
    setIsSubmitting(true);
    
    try {
      // Save settings to localStorage
      localStorage.setItem(`luvhive_settings_${user.username}`, JSON.stringify(settings));
      
      // Update user profile with public/private status
      const updatedUser = {
        ...user,
        isPublic: settings.isPublic,
        settings: settings
      };
      localStorage.setItem('luvhive_user', JSON.stringify(updatedUser));
      
      setTimeout(() => {
        if (onSettingsUpdate) {
          onSettingsUpdate(settings);
        }
        
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert("Settings saved successfully! ✨");
        }
        
        onClose();
      }, 1000);
      
    } catch (error) {
      console.error('Error saving settings:', error);
      setIsSubmitting(false);
    }
  };

  const handleDownloadData = () => {
    if (window.Telegram?.WebApp?.showAlert) {
      window.Telegram.WebApp.showAlert(
        "📱 Data Export Request\n\n" +
        "Your data export will be prepared and sent to your registered email within 24 hours.\n\n" +
        "This includes:\n• Profile information\n• Posts and stories\n• Connections and interactions\n• Settings and preferences"
      );
    } else {
      alert("Data export feature coming soon!");
    }
  };

  const handleHelpSupport = () => {
    if (window.Telegram?.WebApp?.showAlert) {
      window.Telegram.WebApp.showAlert(
        "❓ LuvHive Support\n\n" +
        "Need help? Contact us:\n\n" +
        "📧 Email: support@luvhive.com\n" +
        "💬 Bot: Type /support in LuvHive bot\n" +
        "🌐 Website: luvhive.com/help\n\n" +
        "We're here to help! ✨"
      );
    } else {
      alert("Help & Support: contact support@luvhive.com");
    }
  };

  const handleLogout = () => {
    if (window.Telegram?.WebApp?.showConfirm) {
      window.Telegram.WebApp.showConfirm(
        "Are you sure you want to logout?\n\nYou'll need to register again to access LuvHive.",
        (confirmed) => {
          if (confirmed) {
            performLogout();
          }
        }
      );
    } else {
      // eslint-disable-next-line no-restricted-globals
      if (confirm("Are you sure you want to logout?")) {
        performLogout();
      }
    }
  };

  const performLogout = () => {
    // Clear all user data
    localStorage.removeItem('luvhive_user');
    localStorage.removeItem(`luvhive_settings_${user.username}`);
    localStorage.removeItem(`luvhive_following_${user.username}`);
    localStorage.removeItem(`luvhive_followers_${user.username}`);
    
    if (window.Telegram?.WebApp?.showAlert) {
      window.Telegram.WebApp.showAlert("👋 Logged out successfully! Thanks for using LuvHive.");
    }
    
    onClose();
    
    // Redirect to welcome page after a short delay
    setTimeout(() => {
      window.location.href = '/';
    }, 1000);
  };

  const settingsGroups = [
    {
      title: 'Privacy Controls',
      icon: '🔒',
      settings: [
        {
          key: 'isPublic',
          title: 'Public Profile',
          description: 'Allow anyone to view your profile and posts',
          icon: settings.isPublic ? '🌍' : '🔒'
        },
        {
          key: 'showInSearch',
          title: 'Appear in Search',
          description: 'Let others discover you in search results',
          icon: '🔍'
        },
        {
          key: 'allowMessages',
          title: 'Allow Direct Messages',
          description: 'Let other users send you private messages',
          icon: '💬'
        },
        {
          key: 'showOnlineStatus',
          title: 'Show Online Status',
          description: 'Display when you\'re active on LuvHive',
          icon: '🟢'
        }
      ]
    },
    {
      title: 'Interaction Preferences',
      icon: '💫',
      settings: [
        {
          key: 'allowTagging',
          title: 'Allow Tagging',
          description: 'Let others tag you in posts and stories',
          icon: '🏷️'
        },
        {
          key: 'allowStoryReplies',
          title: 'Story Replies',
          description: 'Allow others to reply to your stories',
          icon: '📖'
        },
        {
          key: 'showVibeScore',
          title: 'Show Vibe Score',
          description: 'Display your vibe compatibility score',
          icon: '🌈'
        },
        {
          key: 'allowLocationSharing',
          title: 'Location Sharing',
          description: 'Share your location in posts (optional)',
          icon: '📍'
        }
      ]
    },
    {
      title: 'Notifications',
      icon: '🔔',
      settings: [
        {
          key: 'pushNotifications',
          title: 'Push Notifications',
          description: 'Receive notifications for sparks, glows, and messages',
          icon: '📱'
        },
        {
          key: 'emailNotifications',
          title: 'Email Notifications',
          description: 'Get email updates about your LuvHive activity',
          icon: '📧'
        }
      ]
    }
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl max-w-md w-full max-h-[90vh] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 sticky top-0 bg-white">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            disabled={isSubmitting}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold">Settings</h2>
          <button
            onClick={handleSave}
            disabled={isSubmitting}
            className={`px-4 py-2 rounded-full font-semibold transition-all ${
              isSubmitting
                ? 'bg-gray-200 text-gray-400'
                : 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg'
            }`}
          >
            {isSubmitting ? '✨' : 'Save'}
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Account Status Banner */}
          <div className={`p-4 rounded-2xl mb-6 ${
            settings.isPublic 
              ? 'bg-gradient-to-r from-green-100 to-emerald-100 border border-green-200' 
              : 'bg-gradient-to-r from-gray-100 to-slate-100 border border-gray-200'
          }`}>
            <div className="flex items-center space-x-3">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                settings.isPublic ? 'bg-green-500' : 'bg-gray-500'
              }`}>
                <span className="text-2xl text-white">
                  {settings.isPublic ? '🌍' : '🔒'}
                </span>
              </div>
              <div>
                <h3 className="font-bold text-gray-800">
                  {settings.isPublic ? 'Public Account' : 'Private Account'}
                </h3>
                <p className="text-sm text-gray-600">
                  {settings.isPublic 
                    ? 'Anyone can see your posts and profile' 
                    : 'Only approved followers can see your posts'
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Settings Groups */}
          {settingsGroups.map((group, groupIndex) => (
            <div key={groupIndex} className="mb-6">
              <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center">
                <span className="mr-2">{group.icon}</span>
                {group.title}
              </h3>
              
              <div className="space-y-3">
                {group.settings.map((setting) => (
                  <div 
                    key={setting.key}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm">
                        <span className="text-lg">{setting.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-800">{setting.title}</h4>
                        <p className="text-sm text-gray-600 leading-relaxed">{setting.description}</p>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleToggle(setting.key)}
                      disabled={isSubmitting}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        settings[setting.key] 
                          ? 'bg-gradient-to-r from-pink-500 to-purple-600' 
                          : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          settings[setting.key] ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Account Actions */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center">
              <span className="mr-2">⚙️</span>
              Account Actions
            </h3>
            
            <div className="space-y-3">
              <button 
                onClick={handleDownloadData}
                className="w-full flex items-center space-x-3 p-4 bg-blue-50 rounded-2xl hover:bg-blue-100 transition-colors"
              >
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white">📱</span>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold text-gray-800">Download Data</h4>
                  <p className="text-sm text-gray-600">Export your LuvHive data</p>
                </div>
              </button>
              
              <button 
                onClick={handleHelpSupport}
                className="w-full flex items-center space-x-3 p-4 bg-yellow-50 rounded-2xl hover:bg-yellow-100 transition-colors"
              >
                <div className="w-10 h-10 bg-yellow-500 rounded-full flex items-center justify-center">
                  <span className="text-white">❓</span>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold text-gray-800">Help & Support</h4>
                  <p className="text-sm text-gray-600">Get help with LuvHive</p>
                </div>
              </button>
              
              <button 
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 p-4 bg-red-50 rounded-2xl hover:bg-red-100 transition-colors"
              >
                <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-white">🚪</span>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold text-gray-800">Logout</h4>
                  <p className="text-sm text-gray-600">Sign out of LuvHive</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;