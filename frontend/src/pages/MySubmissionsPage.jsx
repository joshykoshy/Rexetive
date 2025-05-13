import React from 'react';
import styles from './MySubmissionsPage.module.css';
import { useState, useEffect } from 'react';
import api from '../utils/api';
import { useParams, Link } from 'react-router-dom';
import bg1 from '../assets/bg-1.jpg';
import bg2 from '../assets/bg-2.jpg';
import bg3 from '../assets/bg-3.jpg';
import bg4 from '../assets/bg-4.jpg';
import bg5 from '../assets/bg-5.jpg';

const MySubmissionsPage = () => {
    const { author } = useParams();
    const [submissions, setSubmissions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const backgroundImages = [bg1, bg2, bg3, bg4, bg5];

    useEffect(()=>{
        const fetchSubmissions = async () => {
            try{
                setIsLoading(true);
                const response = await api.get(`/get_all_submissions`);
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
        
        <div className={styles.mySubmissionsPage}>
            <h1 className={styles.pageTitle}>My Submissions</h1>
            <div className={styles.submissionsContainer} id="submissionsContainer">
            {submissions.length > 0 ? (
            submissions
                .filter((submission) => submission.author === author)
                .map((submission) => {
                const randomImage = backgroundImages[Math.floor(Math.random() * backgroundImages.length)];
                return (
                    <Link
                    key={submission.submission_id}
                    to={`/submission/${submission.submission_id}`}
                    className={styles.caseCard}
                    style={{ backgroundImage: `url(${randomImage})` }}
                    >
                    <div className={styles.overlay}></div>
                    <div className={styles.cardContent}>
                        <h3>Case #{submission.caseId}</h3>
                        <p>Submission ID: {submission.submission_id}</p>
                        <p>Author: {submission.author.slice(0, 6)}...{submission.author.slice(-4)}</p>
                        <p>Rank: {submission.rank}</p>
                        <div className={styles.viewDetails}>→</div>
                    </div>
                    </Link>
                );
                })
            ) : (
            <p className={styles.noSubmissions}>No submissions found</p>
            )}

            </div>
        </div>
    );
};

export default MySubmissionsPage;
