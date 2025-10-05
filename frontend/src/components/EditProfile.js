import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom'; // or Next: useRouter

const EditProfile = ({ user, onClose, onSave }) => {
  const [name, setName] = useState(user.name || '');
  const [username, setUsername] = useState(user.username || '');
  const [bio, setBio] = useState(user.bio || '');
  const [profilePic, setProfilePic] = useState(user.profilePic || '');
  const [newProfileImage, setNewProfileImage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const abortControllerRef = useRef(null);
  const ctlRef = useRef(null);
  const navigate = useNavigate();  // or const router = useRouter();

  // Check username change eligibility
  const checkUsernameChangeEligibility = () => {
    const lastUsernameChange = localStorage.getItem(`luvhive_username_change_${user.username}`);
    if (!lastUsernameChange) return { canChange: true, daysLeft: 0 };
    
    const lastChangeDate = new Date(lastUsernameChange);
    const now = new Date();
    const daysSinceChange = Math.floor((now - lastChangeDate) / (1000 * 60 * 60 * 24));
    const daysLeft = Math.max(0, 14 - daysSinceChange);
    
    return { canChange: daysLeft === 0, daysLeft };
  };

  const { canChange: canChangeUsername, daysLeft } = checkUsernameChangeEligibility();

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        (window.Telegram?.WebApp?.showAlert || alert)("Image too large! Max 10MB for profile pictures.");
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        setNewProfileImage(e.target.result);   // base64 preview
        setProfilePic(e.target.result);        // show instantly
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    if (!hasChanges || isSubmitting) return;
    setIsSubmitting(true);
    const avatarVersion = newProfileImage ? Date.now() : (user.avatarVersion || 0);
    const finalProfilePic = profilePic; // ❗ Do NOT append ?v here; Avatar component will add it
    const updatedUser = {
      ...user,
      name: name.trim(),
      username: username.trim(),
      bio: bio.trim(),
      profilePic: finalProfilePic,
      avatarUrl: finalProfilePic,
      avatarVersion
    };
    // (Optional) Try backend avatar upload + profile update
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      if (backendUrl && newProfileImage) {
        // Upload avatar to backend
        const blob = await (await fetch(newProfileImage)).blob();
        const fd = new FormData(); fd.append('file', new File([blob], 'avatar.jpg', { type: blob.type || 'image/jpeg' }));
        const up = await fetch(`${backendUrl}/api/upload-photo`, {
          method: 'POST', body: fd,
          headers: { ...(window.Telegram?.WebApp?.initData ? { 'X-Telegram-Init-Data': window.Telegram.WebApp.initData } : {}) }
        });
        if (up.ok) {
          const js = await up.json().catch(()=> ({}));
          if (js?.photo_url) updatedUser.avatarUrl = js.photo_url;
        }
        // If you add backend /api/profile (below), call it here to persist display_name/bio/avatar
      }
    } catch (e) {
      console.warn('Backend profile update skipped:', e);
    } finally {
      // Always persist locally for immediate UX
      localStorage.setItem('luvhive_user', JSON.stringify(updatedUser));
      setIsSubmitting(false);
      onSave?.(updatedUser);
      onClose?.();
    }
  };

  const handleCancel = () => {
    // Cancel any ongoing operations
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Reset submitting state
    setIsSubmitting(false);
    
    // Close modal
    if (onClose) {
      onClose();
    }
  };

  const hasChanges = name.trim() !== (user.name || '').trim() || 
                    (username.trim() !== (user.username || '').trim() && canChangeUsername) || 
                    bio.trim() !== (user.bio || '').trim() || 
                    newProfileImage;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl overflow-hidden max-h-[95vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <button
            onClick={handleCancel}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            disabled={false} // Always allow cancel
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold">Edit Profile</h2>
          <button
            onClick={handleSave}
            disabled={isSubmitting || !hasChanges}
            className={`px-4 py-2 rounded-full font-semibold transition-all ${
              isSubmitting || !hasChanges
                ? 'bg-gray-200 text-gray-400'
                : 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg'
            }`}
          >
            {isSubmitting ? '✨' : 'Save'}
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(95vh-80px)]">
          <div className="p-6 space-y-6">
          {/* Profile Picture Section */}
          <div className="text-center">
            <h3 className="text-sm font-medium text-gray-700 mb-4">Profile Picture</h3>
            <div className="relative inline-block">
              <div className="w-32 h-32 rounded-full overflow-hidden bg-gradient-to-r from-pink-500 to-purple-600 mx-auto border-4 border-white shadow-lg">
                <img 
                  src={profilePic} 
                  alt="Profile" 
                  className="w-full h-full object-cover" 
                />
              </div>
              <label className="absolute bottom-2 right-2 bg-purple-600 text-white p-3 rounded-full cursor-pointer hover:bg-purple-700 transition-colors shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                  disabled={isSubmitting}
                />
              </label>
            </div>
            <p className="text-sm text-gray-500 mt-2">Tap camera icon to change photo</p>
          </div>

          {/* Editable Fields */}
          <div className="space-y-4">
            {/* Name - Always editable */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your display name"
                maxLength="50"
                className="w-full px-4 py-3 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500 mt-1">You can change this anytime</p>
            </div>

            {/* Username - 14-day cooldown */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">@</span>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                  placeholder="username"
                  maxLength="30"
                  className={`w-full pl-8 pr-4 py-3 border rounded-2xl focus:outline-none transition-all ${
                    canChangeUsername 
                      ? 'border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent'
                      : 'border-gray-300 bg-gray-50 cursor-not-allowed'
                  }`}
                  disabled={isSubmitting || !canChangeUsername}
                />
              </div>
              {canChangeUsername ? (
                <p className="text-xs text-green-600 mt-1">✅ You can change your username now</p>
              ) : (
                <p className="text-xs text-orange-600 mt-1">
                  ⏰ Next username change available in {daysLeft} days
                </p>
              )}
            </div>

            {/* Bio Section */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bio
              </label>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Tell the world something about yourself... ✨"
                rows="4"
                maxLength="150"
                className="w-full px-4 py-3 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                disabled={isSubmitting}
              />
              <div className="flex justify-between text-sm mt-1">
                <span className="text-gray-500">Share your vibe with the world</span>
                <span className={`${bio.length > 140 ? 'text-red-500' : 'text-gray-400'}`}>
                  {bio.length}/150
                </span>
              </div>
            </div>
          </div>

          {/* Read-only fields info */}
          <div className="bg-gray-50 rounded-2xl p-4">
            <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
              <span className="mr-2">ℹ️</span>
              Fixed Profile Information
            </h4>
            <div className="space-y-2 text-sm text-gray-600">
              <p><strong>Age:</strong> {user.age} (Cannot be changed)</p>
              <p><strong>Gender:</strong> {user.gender} (Cannot be changed)</p>
              <p className="text-xs text-gray-500 mt-2">
                Age and gender cannot be modified to maintain account integrity and community safety.
              </p>
            </div>
          </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default EditProfile;