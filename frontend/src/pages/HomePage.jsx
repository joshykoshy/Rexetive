import React from 'react';
import CasesSection from '../components/CasesSection/CasesSection';
import styles from './HomePage.module.css';
import SubmissionsSection from '../components/SubmissionsSection/SubmissionsSection';

const HomePage = ({ showAll = false }) => {
    return (
        <div className={styles.homePage}>
            <CasesSection showAll={showAll} />
            <SubmissionsSection showAll={showAll} />
        </div>
    );
};

export default HomePage;