// CaseSynopsisPage.jsx
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import styles from './CaseSynopsisPage.module.css';
import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';

const CaseSynopsisPage = () => {
    const { id } = useParams();
    const [caseData, setCaseData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({
        caseId: parseInt(id) || 0,
        case: "",
        theory: ""
    });
    const [submissionResult, setSubmissionResult] = useState(null);
    const [showToast, setShowToast] = useState(false);
    const [toastMessage, setToastMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { token } = useAuth();

    useEffect(() => {
        const fetchCaseDetails = async () => {
            try {
                setIsLoading(true);
                const response = await fetch('/data/cases.json');

                if (!response.ok) {
                    throw new Error(`Failed to fetch case details: ${response.status}`);
                }

                const data = await response.json();
                const foundCase = data.find(c => c.id === parseInt(id));

                if (!foundCase) {
                    throw new Error(`Case with ID ${id} not found`);
                }

                setCaseData(foundCase);
                setFormData(prev => ({
                    ...prev,
                    caseId: foundCase.id,
                    case: foundCase.description || ""
                }));
                setIsLoading(false);
            } catch (err) {
                console.error("Error fetching case details:", err);
                setError(err.message);
                setIsLoading(false);
            }
        };

        fetchCaseDetails();
    }, [id]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        
        try {
            console.log("Submitting form data:", formData);
            
            const response = await api.post('/submit_submission/synopsis', formData);
            
            console.log("Response:", response);
            
            const result = response.data;
            console.log("Submission result:", result);
            
            setSubmissionResult(result);
            
            if (result.is_valid) {
                setToastMessage("NFT Minted Successfully!");
            } else {
                setToastMessage("Evaluation Invalid");
            }
            setShowToast(true);
            
            setTimeout(() => {
                setShowToast(false);
            }, 3000);
            
        } catch (err) {
            console.error("Error submitting synopsis:", err);
            setToastMessage(`Submission Error: ${err.message}`);
            setShowToast(true);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (isLoading) {
        return <div className={styles.loading}>Loading case details...</div>;
    }

    if (error) {
        return <div className={styles.error}>Error: {error}</div>;
    }

    return (
        <div className={styles.caseDetailsPageContainer}>
            {showToast && (
                <div className={`${styles.toast} ${submissionResult?.is_valid ? styles.successToast : styles.errorToast}`}>
                    {toastMessage}
                </div>
            )}
            
            <div className={styles.caseDetailsPage}>
                <Link to={`/case/${id}`} className={styles.backButton}>
                    ← Back to Case 
                </Link>
                <div className={styles.caseContent}>
                    <h1 className={styles.caseTitle}>{caseData.title} #{caseData.id}</h1>
                    <div className={styles.caseInfo}>
                        <p className={styles.caseDescription}>{caseData.description}</p>
                        <div className={styles.additionalInfo}>
                            <p>Case ID: {caseData.id}</p>
                            <p>Created: {caseData.createdDate}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className={styles.submissionForm}>
                <h2>Submit Case Synopsis</h2>
                <form onSubmit={handleSubmit}>
                    <div className={styles.formGroup}>
                        <label htmlFor="caseId">Case ID:</label>
                        <input 
                            type="number" 
                            id="caseId" 
                            name="caseId" 
                            value={formData.caseId} 
                            onChange={handleInputChange}
                            disabled
                        />
                    </div>
                    
                    <div className={styles.formGroup}>
                        <label htmlFor="case">Case Description:</label>
                        <textarea 
                            id="case" 
                            name="case" 
                            value={formData.case} 
                            onChange={handleInputChange}
                            rows="5"
                            disabled
                        />
                    </div>
                    
                    <div className={styles.formGroup}>
                        <label htmlFor="theory">Your Synopsis Theory:</label>
                        <textarea 
                            id="theory" 
                            name="theory" 
                            value={formData.theory} 
                            onChange={handleInputChange}
                            rows="10"
                            placeholder="Submit your detailed synopsis theory here..."
                            required
                        />
                    </div>
                    
                    <button 
                        type="submit" 
                        className={styles.submitButton}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Submitting...' : 'Submit Synopsis'}
                    </button>
                </form>
            </div>

            {submissionResult && (
                <div className={styles.evaluationResult}>
                    <h2>Evaluation Results</h2>
                    <div className={styles.resultCard}>
                        <div className={styles.scoreGrid}>
                            <div className={styles.scoreItem}>
                                <h3>Clarity</h3>
                                <div className={styles.scoreValue}>{submissionResult.clarity}/10</div>
                            </div>
                            <div className={styles.scoreItem}>
                                <h3>Plausibility</h3>
                                <div className={styles.scoreValue}>{submissionResult.plausibility}/10</div>
                            </div>
                            <div className={styles.scoreItem}>
                                <h3>Consistency</h3>
                                <div className={styles.scoreValue}>{submissionResult.consistency}/10</div>
                            </div>
                            <div className={styles.scoreItem}>
                                <h3>Relevance</h3>
                                <div className={styles.scoreValue}>{submissionResult.relevance}/10</div>
                            </div>
                        </div>
                        
                        <div className={styles.summarySection}>
                            <h3>AI Summary</h3>
                            <p>{submissionResult.summary}</p>
                        </div>
                        
                        <div className={styles.statusSection}>
                            <div className={styles.statusItem}>
                                <span>Validity:</span> 
                                <span className={submissionResult.is_valid ? styles.validTag : styles.invalidTag}>
                                    {submissionResult.is_valid ? 'Valid' : 'Invalid'}
                                </span>
                            </div>
                            <div className={styles.statusItem}>
                                <span>Safety:</span> 
                                <span className={submissionResult.is_safe ? styles.safeTag : styles.unsafeTag}>
                                    {submissionResult.is_safe ? 'Safe' : 'Unsafe'}
                                </span>
                            </div>
                            <div className={styles.statusItem}>
                                <span>Rank:</span> 
                                <span className={styles.rankTag}>{submissionResult.rank}</span>
                            </div>
                            {submissionResult.flag && (
                                <div className={styles.statusItem}>
                                    <span>Flag:</span> 
                                    <span className={styles.flagTag}>{submissionResult.flag}</span>
                                </div>
                            )}
                        </div>
                        
                        {submissionResult.is_valid && submissionResult.blockchain_tx && (
                            <div className={styles.blockchainSection}>
                                <h3>Blockchain Transaction</h3>
                                <div className={styles.blockchainInfo}>
                                    <p>Submission ID: {submissionResult.submission_id}</p>
                                    <p>NFT Minted: {submissionResult.nft_minted ? 'Yes' : 'No'}</p>
                                    <p>Timestamp: {new Date(submissionResult.timestamp * 1000).toLocaleString()}</p>
                                    <p className={styles.txHash}>TX Hash: {submissionResult.blockchain_tx.hash}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CaseSynopsisPage;