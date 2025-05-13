import React from 'react';
import styles from './ViewSubmissionsPage.module.css';
import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Link } from 'react-router-dom';

const ViewSubmissionsPage = () => {
    const [submissions, setSubmissions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(()=>{
        const fetchSubmissions = async () => {
            try{
                setIsLoading(true);
                const response = await api.get('/get_all_submissions');
                const data = response.data;
                setSubmissions(data);
                setIsLoading(false);
            }catch(err){
                console.error("Error fetching submissions:", err);
                setError(err.message || "Failed to fetch submissions");
                setIsLoading(false);
            }
        }
        fetchSubmissions();
    }, []);
    if (isLoading) {
        return <div className={styles.loading}>Loading submissions...</div>;
    }
    if (error) {
        return <div className={styles.error}>Error: {error}</div>;
    }
    return (
        <div className={styles.viewSubmissionsPage}>
            <h1 className={styles.pageTitle}>View Submissions</h1>
            <div className={styles.submissionsContainer} id="submissionsContainer">
                {submissions.length > 0 ? (
                submissions.map(submission => (
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
            </div>
        </div>
    );
};

export default ViewSubmissionsPage;
