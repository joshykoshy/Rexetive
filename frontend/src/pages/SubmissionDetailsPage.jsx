import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import styles from './SubmissionDetailsPage.module.css';
import api from '../utils/api';

const SubmissionDetailsPage = () => {
    const { id } = useParams();
    const [submission, setSubmission] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSubmissionDetails = async () => {
            try {
                setIsLoading(true);
                // Fetch submission from API
                const response = await api.get(`/get_submission/${id}`);
                setSubmission(response.data);
                setIsLoading(false);
            } catch (err) {
                console.error("Error fetching submission details:", err);
                setError(err.message || "Failed to fetch submission details");
                setIsLoading(false);
            }
        };

        fetchSubmissionDetails();
    }, [id]);

    if (isLoading) {
        return <div className={styles.loading}>Loading submission details...</div>;
    }

    if (error) {
        return <div className={styles.error}>Error: {error}</div>;
    }

    if (!submission) {
        return <div className={styles.notFound}>Submission not found</div>;
    }

    // Calculate total score
    const totalScore = submission.clarity + submission.plausibility + 
                       submission.consistency + submission.relevance;

    // Format timestamp to readable date
    const formattedDate = new Date(submission.timestamp * 1000).toLocaleString();

    return (
        <div className={styles.submissionDetailsPageContainer}>
            <div className={styles.submissionDetailsPage}>
                <Link to="/view-submissions" className={styles.backButton}>
                    ← Back to Submissions
                </Link>
                <div className={styles.submissionContent}>
                    <h1 className={styles.submissionTitle}>Submission for Case #{submission.caseId}</h1>
                    
                    <div className={styles.submissionInfo}>
                        <div className={styles.submissionMeta}>
                            <div className={styles.metaItem}>
                                <strong>Submission ID:</strong> {submission.submission_id}
                            </div>
                            <div className={styles.metaItem}>
                                <strong>Submitted:</strong> {formattedDate}
                            </div>
                            <div className={styles.metaItem}>
                                <strong>Rank:</strong> <span className={styles.rank}>{submission.rank}</span>
                            </div>
                            <div className={styles.metaItem}>
                                <strong>Status:</strong> {submission.is_valid ? 
                                    <span className={styles.valid}>Valid</span> : 
                                    <span className={styles.invalid}>Invalid</span>}
                            </div>
                            
                            <div className={styles.metaItem}>
                                <strong>Author:</strong> {submission.author}
                            </div>
                            {submission.flag && (
                                <div className={`${styles.metaItem} ${styles.flagItem}`}>
                                    <strong>Flag:</strong> <span className={styles.flag}>{submission.flag}</span>
                                </div>
                            )}

                        </div>

                        <div className={styles.scoreSection}>
                            <h3>Evaluation Scores</h3>
                            <div className={styles.scoreGrid}>
                                <div className={styles.scoreItem}>
                                    <div className={styles.scoreLabel}>Clarity</div>
                                    <div className={styles.scoreValue}>{submission.clarity}/10</div>
                                </div>
                                <div className={styles.scoreItem}>
                                    <div className={styles.scoreLabel}>Plausibility</div>
                                    <div className={styles.scoreValue}>{submission.plausibility}/10</div>
                                </div>
                                <div className={styles.scoreItem}>
                                    <div className={styles.scoreLabel}>Consistency</div>
                                    <div className={styles.scoreValue}>{submission.consistency}/10</div>
                                </div>
                                <div className={styles.scoreItem}>
                                    <div className={styles.scoreLabel}>Relevance</div>
                                    <div className={styles.scoreValue}>{submission.relevance}/10</div>
                                </div>
                                <div className={`${styles.scoreItem} ${styles.totalScore}`}>
                                    <div className={styles.scoreLabel}>Total Score</div>
                                    <div className={styles.scoreValue}>{totalScore}/40</div>
                                </div>
                            </div>
                        </div>

                        <div className={styles.theorySection}>
                            <h3>Theory</h3>
                            <div className={styles.theoryContent}>
                                {submission.theory}
                            </div>
                        </div>

                        <div className={styles.summarySection}>
                            <h3>AI Summary</h3>
                            <div className={styles.summaryContent}>
                                {submission.summary}
                            </div>
                        </div>
                        
                        <div className={styles.submissionActions}>
                            <Link to={`/case/${submission.caseId}`} className={styles.actionButton}>
                                View Original Case
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SubmissionDetailsPage;