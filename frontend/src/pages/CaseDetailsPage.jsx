import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import styles from './CaseDetailsPage.module.css';
import CaseAnalysisTools from '../components/CaseAnalysisTools/CaseAnalysisTools';
import  ToolCard  from '../components/CaseAnalysisTools/CaseAnalysisTools';

const CaseDetailsPage = () => {
    const { id } = useParams();
    const [caseData, setCaseData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

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
                setIsLoading(false);
            } catch (err) {
                console.error("Error fetching case details:", err);
                setError(err.message);
                setIsLoading(false);
            }
        };

        fetchCaseDetails();
    }, [id]);

    if (isLoading) {
        return <div className={styles.loading}>Loading case details...</div>;
    }

    if (error) {
        return <div className={styles.error}>Error: {error}</div>;
    }

    return (
        <div className={styles.caseDetailsPageContainer}>
            <div className={styles.caseDetailsPage}>
                <Link to="/all-cases" className={styles.backButton}>
                    ← Back to Cases
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
            <CaseAnalysisTools caseData={caseData} />
        </div>
    );
};

export default CaseDetailsPage;