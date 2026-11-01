import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar/Navbar';
import HomePage from './pages/HomePage';
import CaseDetailsPage from './pages/CaseDetailsPage';
import ViewSubmissionsPage from './pages/ViewSubmissionsPage';
import MySubmissionsPage from './pages/MySubmissionsPage';
import CaseSynopsisPage from './pages/CaseSynopsisPage';
import CaseLogicPage from './pages/CaseLogicPage';
import CaseHypothesisPage from './pages/CaseHypothesisPage';
import CaseBiasPage from './pages/CaseBiasPage';
import ProtectedRoute from './components/ProtectedRoute';
import { ConnectButton } from '@mysten/dapp-kit';
import { Box } from '@radix-ui/themes';
import './App.css';
import SubmissionDetailsPage from './pages/SubmissionDetailsPage';
import ViewCasesPage from './pages/ViewCasesPage';
import ReviewTracePage from './pages/ReviewTracePage';
import ModerationQueuePage from './pages/ModerationQueuePage';
import AnalyticsPage from './pages/AnalyticsPage';
import EvalsPage from './pages/EvalsPage';
import { useAuth, DEMO_MODE } from './contexts/AuthContext';

function LoginScreen() {
  const { walletConnected, loginWithWallet, loginDemo, busy, error } = useAuth();
  return (
    <div className="login-message">
      <h2>Sign in to Rexetive</h2>
      <p>Connect your Sui wallet, then sign a one-time message to prove you own it. Nothing is sent on-chain.</p>
      <Box><ConnectButton /></Box>
      {walletConnected && (
        <button style={{ marginTop: 12 }} disabled={busy} onClick={loginWithWallet}>
          {busy ? 'Waiting for signature...' : 'Sign in with wallet'}
        </button>
      )}
      {DEMO_MODE && (
        <div style={{ marginTop: 24 }}>
          <p style={{ color: '#ffd76a' }}>DEMO MODE: sign in as the demo moderator without a wallet (interview demo only).</p>
          <button disabled={busy} onClick={loginDemo}>Demo login</button>
        </div>
      )}
      {error && <p style={{ color: '#ff9b9b' }}>{error}</p>}
    </div>
  );
}

function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="App">
      {isAuthenticated ? (
        <Router>
          <div className="app">
            <Navbar onLogout={logout} />
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/case/:id" element={<ProtectedRoute><CaseDetailsPage /></ProtectedRoute>} />
              <Route path="/case/:id/synopsis-evaluation" element={<ProtectedRoute><CaseSynopsisPage /></ProtectedRoute>} />
              <Route path="/case/:id/logic-analysis" element={<ProtectedRoute><CaseLogicPage /></ProtectedRoute>} />
              <Route path="/case/:id/hypothesis-verification" element={<ProtectedRoute><CaseHypothesisPage /></ProtectedRoute>} />
              <Route path="/case/:id/bias-detection" element={<ProtectedRoute><CaseBiasPage /></ProtectedRoute>} />
              <Route path="/view-submissions" element={<ProtectedRoute><ViewSubmissionsPage /></ProtectedRoute>} />
              <Route path="/submission/:id" element={<ProtectedRoute><SubmissionDetailsPage /></ProtectedRoute>} />
              <Route path="/my-submissions/:author" element={<ProtectedRoute><MySubmissionsPage /></ProtectedRoute>} />
              <Route path="/all-cases" element={<ViewCasesPage />} />
              <Route path="/review/:id" element={<ProtectedRoute><ReviewTracePage /></ProtectedRoute>} />
              <Route path="/moderation" element={<ProtectedRoute><ModerationQueuePage /></ProtectedRoute>} />
              <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
              <Route path="/evals" element={<ProtectedRoute><EvalsPage /></ProtectedRoute>} />
              <Route path="/login" element={<Navigate to="/" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </Router>
      ) : (
        <LoginScreen />
      )}
    </div>
  );
}

export default App;
