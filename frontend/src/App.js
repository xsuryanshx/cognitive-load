import React, { useState, useEffect } from 'react';
import './App.css';
import TypingTest from './components/TypingTest';
import Auth from './components/Auth';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  useEffect(() => {
    // Check for stored auth
    const storedToken = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLogin = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Keystroke Capture Platform</h1>
        <p>Type the sentences below to help us collect typing data</p>
        {user && (
          <div className="user-info">
            <span>Logged in as: {user.email}</span>
            <button onClick={handleLogout} className="btn-logout">Logout</button>
          </div>
        )}
      </header>
      <main>
        {!user ? (
          <Auth onLogin={handleLogin} />
        ) : (
          <TypingTest user={user} token={token} />
        )}
      </main>
    </div>
  );
}

export default App;

