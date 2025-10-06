import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { hydrateUser } from './state/hydrateUser';
import WelcomePage from './components/WelcomePage';
import SocialFeed from './components/SocialFeed';
import WhatsNew from './components/WhatsNew';
import Discover from './components/Discover';
import RegistrationFlow from './components/RegistrationFlow';
import MyProfile from './pages/MyProfile';

function App() {
  const [user, setUser] = useState(null);
  const [theme] = useState('passion'); // eslint-disable-line no-unused-vars
  const [isRegistered, setIsRegistered] = useState(false);

  useEffect(() => { 
    hydrateUser(); 
    
    // Initialize Telegram WebApp theme
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      const telegramUser = tg.initDataUnsafe?.user; // eslint-disable-line no-unused-vars
      
      // Set theme based on Telegram theme
      if (tg.colorScheme === 'dark') {
        document.body.classList.add('dark');
      }
    }

    // Auto-login function - fetch user from backend if not in localStorage
    const autoLogin = async () => {
      try {
        const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
        const response = await fetch(`${backendUrl}/api/me`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...(window.Telegram?.WebApp?.initData ? {
              'X-Telegram-Init-Data': window.Telegram.WebApp.initData
            } : {}),
            'X-Dev-User': '647778438' // Dev mode fallback
          },
          credentials: 'include'
        });

        if (response.ok) {
          const userData = await response.json();
          console.log('✅ Auto-login successful:', userData.display_name);
          
          // Transform backend data to frontend format
          const user = {
            id: userData.id,
            tg_user_id: userData.id,
            name: userData.display_name,
            display_name: userData.display_name,
            username: userData.username,
            age: userData.age,
            bio: userData.bio || 'LuvHive user ✨',
            mood: '😊',
            avatarUrl: userData.avatar_url,
            avatar_url: userData.avatar_url,
            created_at: userData.created_at || new Date().toISOString(),
            joinDate: new Date(userData.created_at || Date.now()).toLocaleDateString('en-US', {month: 'long', year: 'numeric'}),
            is_onboarded: userData.is_onboarded
          };
          
          // Save to localStorage and set state
          localStorage.setItem('luvhive_user', JSON.stringify(user));
          setUser(user);
          setIsRegistered(true);
          return;
        }
      } catch (error) {
        console.log('⚠️ Auto-login failed:', error.message);
      }
    };

    // Check if user is already registered in localStorage
    const savedUser = localStorage.getItem('luvhive_user');
    console.log('🔍 Checking for existing user in localStorage:', savedUser ? 'Found' : 'Not found');
    
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        console.log('✅ Loading existing user:', userData.name || userData.username);
        setUser(userData);
        setIsRegistered(true);
      } catch (error) {
        console.error('❌ Error parsing saved user data:', error);
        localStorage.removeItem('luvhive_user'); // Remove corrupted data
        autoLogin(); // Try auto-login
      }
    } else {
      console.log('🆕 No existing user found, attempting auto-login...');
      autoLogin(); // Try to fetch user from backend
    }
  }, []);

  const handleRegistrationComplete = (userData) => {
    console.log('🎉 Registration completed, setting user state:', userData);
    setUser(userData);
    setIsRegistered(true);
    
    // Double-check localStorage is set correctly
    const savedUser = localStorage.getItem('luvhive_user');
    console.log('✅ Verified localStorage user data:', savedUser ? 'Present' : 'Missing');
  };

  const handleEnterLuvHive = () => {
    console.log('🎯 handleEnterLuvHive called. isRegistered:', isRegistered, 'user:', user);
    
    if (isRegistered && user) {
      // User is registered, go to feed
      console.log('✅ User already registered, redirecting to feed');
      return '/feed';
    } else {
      // User needs to register
      console.log('📝 User not registered, redirecting to registration');
      return '/register';
    }
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/" 
            element={<WelcomePage user={user} theme={theme} onEnterLuvHive={handleEnterLuvHive} />} 
          />
          <Route 
            path="/register" 
            element={<RegistrationFlow onComplete={handleRegistrationComplete} />} 
          />
          <Route 
            path="/feed" 
            element={<SocialFeed user={user} theme={theme} />} 
          />
          <Route path="/whats-new" element={<WhatsNew theme={theme} />} />
          <Route path="/profile" element={<MyProfile/>} />
          <Route 
            path="/discover" 
            element={<Discover user={user} theme={theme} />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;