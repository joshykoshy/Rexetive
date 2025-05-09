import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Navbar.module.css';
import { AvatarIcon } from '@radix-ui/react-icons';
import { useCurrentAccount, ConnectButton } from '@mysten/dapp-kit';
import api from '../../utils/api';

const Navbar = ({ onLogout }) => {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [userReputation, setUserReputation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const profileRef = useRef(null);
  const navigate = useNavigate();
  const currentAccount = useCurrentAccount();
  const isAuthenticated = !!currentAccount;

  const toggleProfileMenu = () => {
    setShowProfileMenu((prev) => !prev);
  };

  useEffect(() => {
    // Always fetch reputation when the profile menu is opened
    if (showProfileMenu && isAuthenticated && !isLoading) {
      fetchUserReputation();
    }
  }, [showProfileMenu, isAuthenticated]);

  const fetchUserReputation = async () => {
    try {
      setIsLoading(true);
      const response = await api.get('/me/reputation');
      setUserReputation(response.data);
      console.log('User reputation:', response.data);
    } catch (error) {
      console.error('Failed to fetch reputation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClickOutside = (event) => {
    if (profileRef.current && !profileRef.current.contains(event.target)) {
      setShowProfileMenu(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      setShowProfileMenu(false);
    }
  };

  useEffect(() => {
    if (showProfileMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showProfileMenu]);

  const formatWalletAddress = (address) => {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  const handleLogoutClick = () => {
    setShowProfileMenu(false);
    setUserReputation(null);
    if (onLogout) {
      onLogout();  
    }
    navigate('/'); 
  };

  return (
    <nav className={styles.navbar}>
      <Link to="/" className={styles.logo}>Rexetive</Link>
      <div className={styles.navLinks}>
        <Link to="/view-submissions" className={styles.navLink}>View Submissions</Link>
        <Link to={`/my-submissions/${currentAccount?.address}`} className={styles.navLink}>My Submissions</Link>
        <div className={styles.profileContainer} ref={profileRef}>
          {isAuthenticated ? (
            <>
              <button className={styles.profileIcon} onClick={toggleProfileMenu}>
                <AvatarIcon width="30px" height="30px" />
              </button>
              {showProfileMenu && (
                <div className={styles.profileMenu}>
                  <div className={styles.accountDetails}>
                    <p className={styles.userName}>Wallet</p>
                    <p className={styles.userAddress}>
                      {formatWalletAddress(currentAccount?.address)}
                    </p>
                  </div>
                  
                  {userReputation ? (
                    <div className={styles.reputationDetails}>
                      <h4 className={styles.reputationTitle}>Reputation</h4>
                      <div className={styles.reputationStats}>
                        <div className={styles.reputationItem}>
                          <span className={styles.reputationLabel}>Points:</span>
                          <span className={styles.reputationValue}>{userReputation.reputation_points}</span>
                        </div>
                        <div className={styles.reputationItem}>
                          <span className={styles.reputationLabel}>NFTs:</span>
                          <span className={styles.reputationValue}>{userReputation.nft_count}</span>
                        </div>
                        <div className={styles.reputationItem}>
                          <span className={styles.reputationLabel}>Accepted:</span>
                          <span className={styles.reputationValue}>{userReputation.submissions_accepted}</span>
                        </div>
                      </div>
                    </div>
                  ) : isLoading ? (
                    <div className={styles.reputationLoading}>Loading reputation...</div>
                  ) : (
                    <div className={styles.reputationNotFound}>Reputation data not available</div>
                  )}
                  
                  <hr />
                  <button onClick={handleLogoutClick} className={styles.logoutButton}>
                    Logout
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={styles.connectButtonContainer}>
              <ConnectButton connectText="Connect Wallet" />
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
