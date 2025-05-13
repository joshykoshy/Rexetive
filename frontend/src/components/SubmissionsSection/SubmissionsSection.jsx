import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './SubmissionsSection.module.css';
import api from '../../utils/api';

const SubmissionsSection = ({ showAll = false }) => {
  const [submissions, setSubmissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/get_all_submissions');
        setSubmissions(response.data);
        setIsLoading(false);
      } catch (err) {
        console.error("Error fetching submissions:", err);
        setError(err.message || "Failed to fetch submissions");
        setIsLoading(false);
      }
    };

    fetchSubmissions();
  }, []);

  if (isLoading) {
    return <div className={styles.loading}>Loading submissions...</div>;
  }

  if (error) {
    return <div className={styles.error}>Error: {error}</div>;
  }

  const displaySubmissions = showAll ? submissions : submissions.slice(0, 7);

  return (
    <div className={styles.SubmissionsSection}>
      <h2 className={styles.sectionTitle}>Submissions</h2>
      <div className={styles.SubmissionsContainer} id="SubmissionsContainer">
        {displaySubmissions.length > 0 ? (
          displaySubmissions.map(submission => (
            <Link 
              key={submission.submission_id} 
              to={`/submission/${submission.submission_id}`}
              className={styles.caseCard}
            >
              <h3>Case #{submission.caseId}</h3>
              <p>Author: {submission.author.slice(0, 6)}...{submission.author.slice(-4)}</p>
              <p>Rank: {submission.rank}</p>
              <div className={styles.viewDetails}>→</div>
            </Link>
          ))
        ) : (
          <p className={styles.noSubmissions}>No submissions found</p>
        )}
        {!showAll && submissions.length > 7 && (
          <div className={styles.viewAllContainer}>
            <Link to="/view-submissions" className={styles.viewAllButton}>
              View All Submissions
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubmissionsSection;