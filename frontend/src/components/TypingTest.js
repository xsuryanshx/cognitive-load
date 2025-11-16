import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './TypingTest.css';

// Keycode mapping for special keys (matching JavaScript keyCode values)
const KEYCODES = {
  8: 'BKSP',
  9: 'TAB',
  13: 'ENTER',
  16: 'SHIFT',
  17: 'CTRL',
  18: 'ALT',
  20: 'CAPS',
  27: 'ESC',
  32: 'SPACE',
  37: 'LEFT',
  38: 'UP',
  39: 'RIGHT',
  40: 'DOWN',
  46: 'DEL',
};

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Sample sentences for typing test
const SAMPLE_SENTENCES = [
  "Samantha would need around-the-clock care.",
  "The quick brown fox jumps over the lazy dog.",
  "Typing speed tests help improve keyboard skills.",
  "Machine learning models can analyze typing patterns.",
  "Practice makes perfect when learning to type.",
  "Data collection requires careful attention to detail.",
  "User experience design focuses on usability.",
  "Technology continues to evolve at a rapid pace.",
  "Collaboration is key to successful projects.",
  "Innovation drives progress in many fields.",
];

function TypingTest({ user, token }) {
  const [consentGiven, setConsentGiven] = useState(false);
  const [questionCount, setQuestionCount] = useState(10);
  const [questionCountSet, setQuestionCountSet] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);
  const [participantId, setParticipantId] = useState(user?.user_id || null);
  const [testSectionId, setTestSectionId] = useState(null);
  const [allTestSectionIds, setAllTestSectionIds] = useState([]);
  const [currentSentence, setCurrentSentence] = useState('');
  const [userInput, setUserInput] = useState('');
  const [sentenceIndex, setSentenceIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Set up axios interceptor for auth token
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    return () => {
      delete axios.defaults.headers.common['Authorization'];
    };
  }, [token]);
  
  // Metrics
  const [wpm, setWpm] = useState(0);
  const [errorRate, setErrorRate] = useState(0);
  const [accuracy, setAccuracy] = useState(100);
  const [keystrokeCount, setKeystrokeCount] = useState(0);
  const [currentSentenceKeystrokes, setCurrentSentenceKeystrokes] = useState([]);
  const [testComplete, setTestComplete] = useState(false);
  const [finalStats, setFinalStats] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  const inputRef = useRef(null);
  const keystrokeBufferRef = useRef([]);
  const unresolvedKeypressesRef = useRef([]);
  const keyFlagsRef = useRef({});
  const sentenceStartTimeRef = useRef(null);

  // Initialize key flags
  useEffect(() => {
    keyFlagsRef.current = {};
  }, []);

  // Create session when user gives consent
  const createSession = useCallback(async () => {
    if (!user || !token) {
      setError('Please login first');
      return;
    }
    
    try {
      setTestComplete(false);
      setFinalStats(null);
      setSuccess(null);
      setError(null);
      setSentenceIndex(0);
      setCurrentSentence('');
      setUserInput('');
      setAllTestSectionIds([]);
      setKeystrokeCount(0);
      setCurrentSentenceKeystrokes([]);
      keystrokeBufferRef.current = [];
      unresolvedKeypressesRef.current = [];
      keyFlagsRef.current = {};

      const response = await axios.post(`${API_BASE_URL}/api/session`, {
        participant_id: null, // Server will use authenticated user_id
        question_count: questionCount,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const newParticipantId = response.data.participant_id;
      setParticipantId(newParticipantId);
      setSessionStarted(true);
      setCurrentSentence(SAMPLE_SENTENCES[0]);
      setError(null);
      // Create first test section with the new participant ID
      // Note: createTestSection is called directly, not as a dependency
      await createTestSection(SAMPLE_SENTENCES[0], newParticipantId);
    } catch (err) {
      setError(`Failed to create session: ${err.response?.data?.detail || err.message}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, token, questionCount]);

  // Create a new test section for a sentence
  const createTestSection = useCallback(async (sentence, pId = null) => {
    const pid = pId || participantId;
    if (!pid) return;
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/test-section`, {
        participant_id: pid,
        sentence: sentence,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const newTestSectionId = response.data.test_section_id;
      setTestSectionId(newTestSectionId);
      setAllTestSectionIds((prev) => [...prev, newTestSectionId]);
      setCurrentSentenceKeystrokes([]);
      return newTestSectionId;
    } catch (err) {
      console.error('Failed to create test section:', err);
      setError(`Failed to create test section: ${err.response?.data?.detail || err.message}`);
    }
  }, [participantId, token]);

  // Calculate WPM using 136m formula: WPM = 60000 / ((inputTime / inputLength) * 5)
  const calculateWPM = useCallback((keystrokes) => {
    if (!keystrokes || keystrokes.length === 0) return 0;
    
    const firstPress = keystrokes[0].press_time;
    const lastRelease = keystrokes[keystrokes.length - 1].release_time;
    const inputTime = lastRelease - firstPress;
    
    // Count actual characters typed (excluding special keys)
    const inputLength = keystrokes.filter(
      ks => ks.letter && !['SHIFT', 'CTRL', 'ALT', 'CAPS', 'ESC', 'TAB', 'BKSP'].includes(ks.letter)
    ).length;
    
    if (inputTime <= 0 || inputLength === 0) return 0;
    
    // 136m formula: WPM = 60000 / ((inputTime / inputLength) * 5)
    const wpm = 60000 / ((inputTime / inputLength) * 5);
    return Math.round(wpm);
  }, []);

  // Calculate error rate
  const calculateErrorRate = useCallback((sentence, input) => {
    if (!sentence || !input) return 0;
    
    const sentenceChars = sentence.trim().split('');
    const inputChars = input.trim().split('');
    
    let errors = 0;
    const maxLength = Math.max(sentenceChars.length, inputChars.length);
    
    for (let i = 0; i < maxLength; i++) {
      if (i >= sentenceChars.length || i >= inputChars.length) {
        errors++;
      } else if (sentenceChars[i] !== inputChars[i]) {
        errors++;
      }
    }
    
    if (maxLength === 0) return 0;
    return Math.round((errors / maxLength) * 100);
  }, []);

  // Update metrics
  useEffect(() => {
    if (!isTyping || currentSentenceKeystrokes.length === 0) {
      if (!testComplete) {
        setWpm(0);
        setErrorRate(0);
        setAccuracy(100);
      }
      return;
    }

    const interval = setInterval(() => {
      const currentWpm = calculateWPM(currentSentenceKeystrokes);
      setWpm(currentWpm);
      
      const currentErrorRate = calculateErrorRate(currentSentence, userInput);
      setErrorRate(currentErrorRate);
      setAccuracy(100 - currentErrorRate);
    }, 100);

    return () => clearInterval(interval);
  }, [isTyping, currentSentenceKeystrokes, currentSentence, userInput, calculateWPM, calculateErrorRate, testComplete]);

  // Save keystrokes to backend
  const saveKeystrokes = useCallback(async (keystrokes, sentence, input, testSectionId) => {
    if (!keystrokes.length || !testSectionId || !participantId) return;

    try {
      await axios.post(`${API_BASE_URL}/api/keystrokes`, {
        participant_id: participantId,
        test_section_id: testSectionId,
        sentence: sentence,
        user_input: input,
        keystrokes: keystrokes,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      keystrokeBufferRef.current = [];
    } catch (err) {
      console.error('Failed to save keystrokes:', err);
      // Keep keystrokes in buffer for retry
    }
  }, [participantId, token]);

  // Handle keydown event
  const handleKeyDown = useCallback((event) => {
    if (!sessionStarted || !isTyping) return;

    const keyCode = event.keyCode || event.which;
    
    // Prevent default for special keys
    if ([9, 37, 38, 39, 40].includes(keyCode)) {
      event.preventDefault();
    }

    // Check if key is already down (key repeat)
    if (keyFlagsRef.current[keyCode]) {
      if (keyCode >= 65 && keyCode <= 90) {
        // Remove last character for repeated letter keys
        setUserInput((prev) => prev.slice(0, -1));
      }
      return;
    }

    keyFlagsRef.current[keyCode] = true;

    // Get letter representation
    let letter = KEYCODES[keyCode];
    if (!letter) {
      if (event.key && event.key.length === 1) {
        letter = event.key;
      } else {
        letter = String.fromCharCode(keyCode);
      }
    }

    const pressTime = Date.now();
    
    // Create unresolved keypress
    const unresolved = {
      keydown: event,
      letter: letter,
      keycode: keyCode,
      downTime: pressTime,
    };

    unresolvedKeypressesRef.current.push(unresolved);
  }, [sessionStarted, isTyping]);

  // Handle keypress event (for actual character)
  const handleKeyPress = useCallback((event) => {
    if (!sessionStarted || !isTyping) return;

    const time = Date.now();
    const keyCode = event.keyCode || event.which;

    // Update unresolved keypress with actual character
    for (let i = 0; i < unresolvedKeypressesRef.current.length; i++) {
      const unresolved = unresolvedKeypressesRef.current[i];
      if (!unresolved) continue;
      
      if (unresolved.downTime >= time - 20 && unresolved.downTime <= time) {
        if (event.key && event.key.length === 1) {
          unresolved.letter = event.key;
        } else {
          unresolved.letter = String.fromCharCode(keyCode);
        }
        break;
      }
    }
  }, [sessionStarted, isTyping]);

  // Handle keyup event
  const handleKeyUp = useCallback((event) => {
    if (!sessionStarted || !isTyping) return;

    const releaseTime = Date.now();
    const keyCode = event.keyCode || event.which;

    // Find matching unresolved keypress
    for (let i = 0; i < unresolvedKeypressesRef.current.length; i++) {
      const unresolved = unresolvedKeypressesRef.current[i];
      if (!unresolved || !unresolved.letter) continue;

      if (unresolved.keycode === keyCode) {
        // Create keystroke event
        const keystroke = {
          press_time: unresolved.downTime,
          release_time: releaseTime,
          keycode: unresolved.keycode,
          letter: unresolved.letter,
        };

        keystrokeBufferRef.current.push(keystroke);
        setCurrentSentenceKeystrokes((prev) => [...prev, keystroke]);
        setKeystrokeCount((prev) => prev + 1);

        // Save every 5 keystrokes (matching 136m behavior)
        if (keystrokeBufferRef.current.length >= 5) {
          saveKeystrokes(
            [...keystrokeBufferRef.current],
            currentSentence,
            userInput,
            testSectionId
          );
        }

        // Remove from unresolved
        unresolvedKeypressesRef.current.splice(i, 1);
        break;
      }
    }

    keyFlagsRef.current[keyCode] = false;
  }, [sessionStarted, isTyping, currentSentence, userInput, testSectionId, saveKeystrokes]);

  // Set up event listeners
  useEffect(() => {
    if (!sessionStarted) return;

    const inputElement = inputRef.current;
    if (!inputElement) return;

    inputElement.addEventListener('keydown', handleKeyDown);
    inputElement.addEventListener('keypress', handleKeyPress);
    inputElement.addEventListener('keyup', handleKeyUp);

    // Prevent paste
    inputElement.addEventListener('paste', (e) => e.preventDefault());

    return () => {
      inputElement.removeEventListener('keydown', handleKeyDown);
      inputElement.removeEventListener('keypress', handleKeyPress);
      inputElement.removeEventListener('keyup', handleKeyUp);
    };
  }, [sessionStarted, handleKeyDown, handleKeyPress, handleKeyUp]);

  // Handle input change
  const handleInputChange = (e) => {
    const value = e.target.value;
    setUserInput(value);
  };

  // Handle sentence completion
  const handleSentenceComplete = async () => {
    if (testComplete) return;
    // Save remaining keystrokes
    if (keystrokeBufferRef.current.length > 0 && testSectionId && participantId) {
      const batch = {
        participant_id: participantId,
        test_section_id: testSectionId,
        sentence: currentSentence,
        user_input: userInput,
        keystrokes: [...keystrokeBufferRef.current]
      };
      
      // Save to CSV
      await saveKeystrokes(
        batch.keystrokes,
        currentSentence,
        userInput,
        testSectionId
      );
      
      // Trigger Databricks ingestion (real-time after sentence completion)
      try {
        await axios.post(`${API_BASE_URL}/api/sentence-complete`, batch, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      } catch (err) {
        console.error('Failed to ingest to Databricks:', err);
        // Continue even if Databricks fails
      }
    }

    setIsTyping(false);
    setUserInput('');
    unresolvedKeypressesRef.current = [];
    keyFlagsRef.current = {};
    setCurrentSentenceKeystrokes([]);
    keystrokeBufferRef.current = [];

    // Move to next sentence (limited by questionCount)
    const maxQuestions = Math.min(questionCount, SAMPLE_SENTENCES.length);
    if (sentenceIndex < maxQuestions - 1) {
      const nextIndex = sentenceIndex + 1;
      setSentenceIndex(nextIndex);
      const nextSentence = SAMPLE_SENTENCES[nextIndex];
      setCurrentSentence(nextSentence);
      // Create new test section for next sentence
      await createTestSection(nextSentence);
    } else {
      // Test complete naturally (reached question count)
      await endTest();
    }
  };

  // End test (early termination or natural completion)
  const endTest = async () => {
    if (testComplete) return;
    // Save any remaining keystrokes
    if (keystrokeBufferRef.current.length > 0 && testSectionId) {
      await saveKeystrokes(
        [...keystrokeBufferRef.current],
        currentSentence,
        userInput,
        testSectionId
      );
    }

    // Show saving progress
    setIsUploading(true);
    setError(null);
    setSuccess(null);

    // Call backend to finalize test
    try {
      const response = await axios.post(`${API_BASE_URL}/api/end-test`, {
        participant_id: participantId,
        test_section_ids: allTestSectionIds,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setIsUploading(false);
      
      // Data is saved locally
      setSuccess('Test completed! Data saved locally.');
      
      setSessionStarted(false);
      setIsTyping(false);
      const summaryStats = {
        wpm,
        accuracy,
        errorRate,
        keystrokes: keystrokeCount,
        sentences: allTestSectionIds.length,
      };
      setFinalStats(summaryStats);
      setTestComplete(true);
    } catch (err) {
      setIsUploading(false);
      setError(`Error ending test: ${err.message}`);
    }
  };

  // Start typing
  const handleStartTyping = () => {
    if (!sessionStarted) {
      createSession();
      return;
    }
    setIsTyping(true);
    sentenceStartTimeRef.current = Date.now();
    inputRef.current?.focus();
  };

  // Handle Enter key to complete sentence
  const handleKeyDownEnter = (e) => {
    if (e.key === 'Enter' && isTyping && userInput.trim()) {
      e.preventDefault();
      handleSentenceComplete();
    }
  };

  const handleRestartTest = () => {
    setTestComplete(false);
    setFinalStats(null);
    setSuccess(null);
    setError(null);
    setIsUploading(false);
    setSessionStarted(false);
    setIsTyping(false);
    setSentenceIndex(0);
    setCurrentSentence('');
    setUserInput('');
    setAllTestSectionIds([]);
    setParticipantId(user?.user_id || null);
    setTestSectionId(null);
    setCurrentSentenceKeystrokes([]);
    setKeystrokeCount(0);
    keystrokeBufferRef.current = [];
    unresolvedKeypressesRef.current = [];
    keyFlagsRef.current = {};
  };

  if (!consentGiven) {
    return (
      <div className="consent-screen">
        <div className="consent-box">
          <h2>Data Collection Consent</h2>
          <p>
            This typing test collects keystroke data including:
          </p>
          <ul>
            <li>Key press and release timestamps</li>
            <li>Characters typed</li>
            <li>Key codes</li>
            <li>Typing patterns</li>
          </ul>
          <p>
            This data will be used for machine learning research. Your participation is voluntary.
          </p>
          <div className="consent-actions">
            <button
              className="btn btn-primary"
              onClick={() => setConsentGiven(true)}
            >
              I Consent
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => setError('Consent required to participate')}
            >
              Decline
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!questionCountSet) {
    return (
      <div className="consent-screen">
        <div className="consent-box">
          <h2>Test Configuration</h2>
          <p>
            How many questions would you like to answer?
          </p>
          <div style={{ margin: '20px 0' }}>
            <input
              type="number"
              min="1"
              max={SAMPLE_SENTENCES.length}
              value={questionCount}
              onChange={(e) => {
                const count = parseInt(e.target.value) || 10;
                setQuestionCount(Math.max(1, Math.min(count, SAMPLE_SENTENCES.length)));
              }}
              style={{
                padding: '10px',
                fontSize: '18px',
                width: '100px',
                textAlign: 'center',
                border: '2px solid #4CAF50',
                borderRadius: '5px'
              }}
            />
            <p style={{ marginTop: '10px', color: '#666' }}>
              (Maximum: {SAMPLE_SENTENCES.length} questions)
            </p>
          </div>
          <div className="consent-actions">
            <button
              className="btn btn-primary"
              onClick={() => setQuestionCountSet(true)}
            >
              Start Test
            </button>
          </div>
        </div>
      </div>
    );
  }

  const maxQuestions = Math.min(questionCount, SAMPLE_SENTENCES.length);
  const progress = ((sentenceIndex + 1) / maxQuestions) * 100;
  const statsToDisplay = testComplete && finalStats ? finalStats : { wpm, accuracy, errorRate };
  const keystrokesToDisplay = testComplete && finalStats ? finalStats.keystrokes : keystrokeCount;
  const completedSentences = testComplete && finalStats ? finalStats.sentences : allTestSectionIds.length;

  return (
    <div className="typing-test-container">
      <div className="typing-test">
        <div className="typing-header">
          <h2>Typing Test</h2>
          <p>Type the sentence exactly as shown. Press Enter to submit.</p>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Words per minute</span>
            <span className="stat-value">{statsToDisplay.wpm || 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Accuracy</span>
            <span className="stat-value">{statsToDisplay.accuracy || 0}%</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Error rate</span>
            <span className="stat-value">{statsToDisplay.errorRate || 0}%</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Keystrokes</span>
            <span className="stat-value">{keystrokesToDisplay}</span>
          </div>
        </div>

        <div className="progress-section">
          <div className="progress-info">
            <span className="progress-text">
              Sentence {Math.min(sentenceIndex + 1, maxQuestions)} of {maxQuestions}
            </span>
            <span className="progress-percentage">{Math.round(progress)}%</span>
          </div>
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
        </div>

        {error && (
          <div className="message error-message">
            {error}
          </div>
        )}

        {isUploading && (
          <div className="upload-progress-container">
            <div className="upload-progress-header">
              <span className="upload-progress-text">Saving data locally...</span>
            </div>
            <div className="upload-progress-bar-container">
              <div className="upload-progress-bar"></div>
            </div>
          </div>
        )}

        {success && (
          <div className="message success-message">
            {success}
          </div>
        )}

        {testComplete ? (
          <div className="result-card">
            <h3>All done!</h3>
            <p>The test is finished. Thanks for participating.</p>
            <div className="result-stats">
              <div>
                <span className="stat-label">Sentences completed</span>
                <span className="stat-value">{completedSentences}</span>
              </div>
              <div>
                <span className="stat-label">Words per minute</span>
                <span className="stat-value">{statsToDisplay.wpm || 0}</span>
              </div>
              <div>
                <span className="stat-label">Accuracy</span>
                <span className="stat-value">{statsToDisplay.accuracy || 0}%</span>
              </div>
              <div>
                <span className="stat-label">Keystrokes</span>
                <span className="stat-value">{keystrokesToDisplay}</span>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="sentence-display">
              <p className="target-sentence">{currentSentence || 'Loading...'}</p>
            </div>

            <div className="input-section">
              <textarea
                ref={inputRef}
                className="typing-input"
                value={userInput}
                onChange={handleInputChange}
                onKeyDown={handleKeyDownEnter}
                placeholder={isTyping ? 'Start typing...' : "Click 'Start Test' to begin"}
                disabled={!isTyping || testComplete || isUploading}
                rows={4}
              />
              <small className="helper-text">
                Press Enter to submit the current sentence when you are done.
              </small>
            </div>
          </>
        )}

        <div className="actions">
          {testComplete ? (
            <button className="btn btn-primary" onClick={handleRestartTest} disabled={isUploading}>
              Start New Test
            </button>
          ) : !sessionStarted ? (
            <button className="btn btn-primary" onClick={handleStartTyping} disabled={isUploading}>
              Start Test
            </button>
          ) : !isTyping ? (
            <div className="action-group">
              <button className="btn btn-primary" onClick={handleStartTyping} disabled={isUploading}>
                Resume Typing
              </button>
              <button className="btn btn-ghost" onClick={endTest} disabled={isUploading}>
                End Test
              </button>
            </div>
          ) : (
            <div className="action-group">
              <button
                className="btn btn-secondary"
                onClick={handleSentenceComplete}
                disabled={isUploading}
              >
                Complete Sentence
              </button>
              <button className="btn btn-ghost" onClick={endTest} disabled={isUploading}>
                End Test
              </button>
            </div>
          )}
        </div>

        {sessionStarted && !testComplete && (
          <div className="session-info">
            <small>
              Participant ID: {participantId?.substring(0, 8)}... | 
              Test Sections: {allTestSectionIds.length}
            </small>
          </div>
        )}
      </div>
    </div>
  );
}

export default TypingTest;
