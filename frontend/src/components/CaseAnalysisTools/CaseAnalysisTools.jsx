import React from 'react';
import {
    MagnifyingGlassIcon,
    ClockIcon,
    InfoCircledIcon,
    FaceIcon
} from '@radix-ui/react-icons';
import styles from './CaseAnalysisTools.module.css';
import { Link } from 'react-router-dom';


const ToolCard = ({ icon, title, description, actionText, onClick }) => {
    return (
        <div className={styles.toolCard}>
            <div className={styles.iconContainer}>
                {icon}
            </div>
            <h3 className={styles.toolTitle}>{title}</h3>
            <p className={styles.toolDescription}>{description}</p>
            <button
                onClick={onClick}
                className={styles.actionButton}
            >
                {actionText} <span className={styles.arrow}>→</span>
            </button>
        </div>
    );
};


const CaseAnalysisTools = ({ caseData }) => {
    // Handler functions for each tool
    const handleSynopsisEvaluation = () => {
        console.log('Evaluating case synopsis for case:', caseData?.id);
    };

    const handleTimelineAnalysis = () => {
        console.log('Analyzing inconsistencies and timeline for case:', caseData?.id);
    };

    const handleHypothesisVerification = () => {
        console.log('Verifying hypothesis for case:', caseData?.id);
    };

    const handleBiasDetection = () => {
        console.log('Detecting bias in case:', caseData?.id);
    };


    return (
        <div className={styles.toolsContainer}>
            <h2 className={styles.sectionTitle}>Case Analysis Tools</h2>

            <div className={styles.toolsGrid}>
                <Link to={`/case/${caseData.id}/synopsis-evaluation`}>
                    <ToolCard
                        icon={<MagnifyingGlassIcon className={styles.toolIcon} />}
                        title="Case Synopsis Evaluation"
                        description="AI evaluates each submission for clarity, plausibility, and logical consistency, producing structured scores and feedback."
                        actionText="Try it now"
                        onClick={handleSynopsisEvaluation}
                    />
                </Link>
                <Link to={`/case/${caseData.id}/logic-analysis`}>
                    <ToolCard
                        icon={<ClockIcon className={styles.toolIcon} />}
                        title="Inconsistency & Timeline Analysis"
                        description="Flags contradictions in timelines or narratives, like impossible locations or unsupported motives."
                        actionText="Learn more"
                        onClick={handleTimelineAnalysis}
                    />
                </Link>
                <Link to={`/case/${caseData.id}/hypothesis-verification`}>
                    <ToolCard
                        icon={<InfoCircledIcon className={styles.toolIcon} />}
                        title="Hypothesis Verification"
                        description="Get evidence-based counterpoints or validation for your theories to encourage critical thinking."
                        actionText="Ask AI"
                        onClick={handleHypothesisVerification}
                    />
                </Link>
                <Link to={`/case/${caseData.id}/bias-detection`}>
                    <ToolCard
                        icon={<FaceIcon className={styles.toolIcon} />}
                        title="Bias Detection"
                        description="Identifies confirmation bias or logical fallacies, prompting users to rethink assumptions."
                        actionText="Test your theory"
                        onClick={handleBiasDetection}
                    />
                </Link>
            </div>
        </div>
    );
};

// CSS Module file needed: CaseAnalysisTools.module.css

export default CaseAnalysisTools;