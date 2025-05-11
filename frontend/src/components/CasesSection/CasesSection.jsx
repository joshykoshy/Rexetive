import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './CasesSection.module.css';

const CasesSection = ({ showAll = false }) => {
  const [cases, setCases] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchCases = async () => {
      try {
        setIsLoading(true);
        const response = await fetch('/data/cases.json');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch cases: ${response.status}`);
        }
        
        const data = await response.json();
        setCases(data);
        setIsLoading(false);
      } catch (err) {
        console.error("Error fetching cases:", err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchCases();
  }, []);

  if (isLoading) {
    return <div className={styles.loading}>Loading cases...</div>;
  }

  if (error) {
    return <div className={styles.error}>Error: {error}</div>;
  }

  const displayCases = showAll ? cases : cases.slice(0, 7);

  return (
    <div className={styles.casesSection}>
      <h2 className={styles.sectionTitle}>Cases</h2>
      <div className={styles.casesContainer} id="casesContainer">
        {displayCases.map(caseItem => (
          <Link 
            key={caseItem.id} 
            to={`/case/${caseItem.id}`}
            className={styles.caseCard}
          >
            <h3>{caseItem.title} #{caseItem.id}</h3>
            <div className={styles.viewDetails}>→</div>
          </Link>
        ))}
        {!showAll && (
          <div className={styles.viewAllContainer}>
            <Link to="/all-cases" className={styles.viewAllButton}>
              View All Cases
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default CasesSection;