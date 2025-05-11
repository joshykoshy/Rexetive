import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './LoginPage.module.css';
import { ConnectButton } from '@mysten/dapp-kit';
import { useAuth } from '../contexts/AuthContext';

const LoginPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loading } = useAuth();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !loading) {
      navigate('/');
    }
  }, [isAuthenticated, loading, navigate]);

  return (
    <div className={styles.loginPage}>
      <div className={styles.loginContainer}>
        <h1 className={styles.title}>Connect Your Wallet</h1>
        <p className={styles.description}>
          Connect your Sui wallet to access the platform. We use your wallet address for authentication.
        </p>
        
        <div className={styles.walletSection}>
          <h2 className={styles.sectionTitle}>Connect with Sui Wallet</h2>
          <div className={styles.connectButtonContainer}>
            <ConnectButton connectText="Connect Your Wallet" />
          </div>
          <p className={styles.walletNote}>
            Don't have a Sui wallet? Get one from the{' '}
            <a 
              href="https://chrome.google.com/webstore/detail/sui-wallet/opcgpfmipidbgpenhmajoajpbobppdil" 
              target="_blank" 
              rel="noopener noreferrer"
              className={styles.walletLink}
            >
              Chrome Web Store
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;