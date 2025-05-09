import React, { createContext, useContext, useState, useEffect } from 'react';
import { useCurrentAccount } from '@mysten/dapp-kit';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const currentAccount = useCurrentAccount();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (currentAccount) {
      // Store wallet address in localStorage for API interceptor
      localStorage.setItem('wallet_address', currentAccount.address);
      
      // Set basic user info
      setUser({
        wallet_address: currentAccount.address
      });
      setLoading(false);
    } else {
      // Clear auth when wallet disconnects
      setUser(null);
      localStorage.removeItem('wallet_address');
      setLoading(false);
    }
  }, [currentAccount]);
  
  const logout = () => {
    setUser(null);
    localStorage.removeItem('wallet_address');
  };
  
  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!currentAccount,
        loading,
        logout
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