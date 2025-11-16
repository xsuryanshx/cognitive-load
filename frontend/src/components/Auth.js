import React, { useState } from 'react';
import axios from 'axios';
import './Auth.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
          email,
          password,
        });
        
        // Store token
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        // Call onLogin callback with user data
        onLogin(response.data.user, response.data.access_token);
      } else {
        // Register
        const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
          email,
          password,
        });
        
        // After registration, automatically login
        const loginResponse = await axios.post(`${API_BASE_URL}/api/auth/login`, {
          email,
          password,
        });
        
        localStorage.setItem('access_token', loginResponse.data.access_token);
        localStorage.setItem('user', JSON.stringify(loginResponse.data.user));
        
        onLogin(loginResponse.data.user, loginResponse.data.access_token);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h2>{isLogin ? 'Login' : 'Register'}</h2>
        <p className="auth-subtitle">
          {isLogin 
            ? 'Sign in to start your typing test' 
            : 'Create an account to participate'}
        </p>

        {error && (
          <div className="auth-error">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your.email@example.com"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              placeholder={isLogin ? "Enter your password" : "At least 6 characters"}
              disabled={loading}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary btn-large"
            disabled={loading}
          >
            {loading ? 'Please wait...' : (isLogin ? 'LOGIN' : 'REGISTER')}
          </button>
        </form>

        <div className="auth-switch">
          <p>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setIsLogin(!isLogin);
                setError(null);
              }}
              disabled={loading}
            >
              {isLogin ? 'Register' : 'Login'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Auth;

