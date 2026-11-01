import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useCurrentAccount, useSignPersonalMessage } from '@mysten/dapp-kit';
import api from '../utils/api';

// Login = prove you own the wallet: the server sends a one-time message, the wallet signs it,
// the server verifies the signature and returns a JWT. VITE_DEMO_MODE=true adds a clearly
// labelled demo login that skips the wallet (the backend must also run with DEMO_MODE=true).
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const currentAccount = useCurrentAccount();
  const { mutateAsync: signPersonalMessage } = useSignPersonalMessage();
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('rex_user') || 'null'));
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const saveSession = (data) => {
    localStorage.setItem('rex_token', data.access_token);
    localStorage.setItem('rex_user', JSON.stringify({ ...data.user, demo: !!data.warning }));
    setUser({ ...data.user, demo: !!data.warning });
  };

  const loginWithWallet = useCallback(async () => {
    if (!currentAccount) return;
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.get('/auth/nonce', { params: { address: currentAccount.address } });
      const { signature } = await signPersonalMessage({ message: new TextEncoder().encode(data.message) });
      const res = await api.post('/auth/verify', {
        address: currentAccount.address,
        message: data.message,
        signature,
      });
      saveSession(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }, [currentAccount, signPersonalMessage]);

  const loginDemo = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post('/auth/demo-login');
      saveSession(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('rex_token');
    localStorage.removeItem('rex_user');
    setUser(null);
  };

  // A different wallet connected: the old session no longer matches it.
  useEffect(() => {
    if (user && !user.demo && currentAccount && currentAccount.address !== user.wallet_address) {
      logout();
    }
  }, [currentAccount, user]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isModerator: user?.role === 'moderator',
        loading: false,
        busy,
        error,
        walletConnected: !!currentAccount,
        loginWithWallet,
        loginDemo,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
