import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import styles from './CaseHypothesisPage.module.css';
import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';

const CaseHypothesisPage = () => {
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
    const [submissionError, setSubmissionError] = useState(false);
    const { token } = useAuth();

    useEffect(() => {
        const fetchCaseDetails = async () => {
            try {
                setIsLoading(true);
                // Fetch data from the JSON file
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
            
            const response = await api.post('/submit_submission/hypothesis', formData);
            
            console.log("Response:", response);
            
            const result = response.data;
            console.log("Hypothesis evaluation result:", result);
            
            setSubmissionResult(result);
            
            setToastMessage("Hypothesis evaluation complete!");
            setShowToast(true);
            
            setTimeout(() => {
                setShowToast(false);
            }, 3000);
            
        } catch (err) {
            console.error("Error submitting hypothesis:", err);
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
                <div className={`${styles.toast} ${submissionError ? styles.errorToast : styles.successToast}`}>
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
                <h2>Submit Hypothesis</h2>
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
                        <label htmlFor="theory">Your Hypothesis:</label>
                        <textarea 
                            id="theory" 
                            name="theory" 
                            value={formData.theory} 
                            onChange={handleInputChange}
                            rows="10"
                            placeholder="Submit your detailed hypothesis here..."
                            required
                        />
                    </div>
                    
                    <button 
                        type="submit" 
                        className={styles.submitButton}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Evaluating...' : 'Submit Hypothesis'}
                    </button>
                </form>
            </div>

            {submissionResult && (
                <div className={styles.evaluationResult}>
                    <h2>Hypothesis Evaluation Results</h2>
                    <div className={styles.resultCard}>
                        <div className={styles.plausibilitySection}>
                            <h3>Plausibility Assessment</h3>
                            <div className={styles.scoreValue}>
                                {submissionResult.plausibility_assessment}/10
                            </div>
                        </div>
                        
                        <div className={styles.counterpointsSection}>
                            <h3>Key Counterpoints</h3>
                            <ul className={styles.counterpointsList}>
                                {submissionResult.counterpoints.map((item, index) => (
                                    <li key={index} className={styles.counterpointItem}>
                                        {item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                        
                        <div className={styles.evidenceSection}>
                            <h3>Evidence Match Analysis</h3>
                            <p>{submissionResult.evidence_match}</p>
                        </div>
                        
                        <div className={styles.investigationSection}>
                            <h3>Suggested Further Investigation</h3>
                            <p>{submissionResult.suggest_further_investigation}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CaseHypothesisPage;