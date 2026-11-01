import React from 'react';
import { Link } from 'react-router-dom';
import s from '../pages/v2.module.css';

// Shown on every mode page after submitting: the gate's decision and a link to the full trace.
export function VerdictBadge({ status }) {
  const cls = { accepted: s.accept, accept: s.accept, rejected: s.reject, reject: s.reject,
                needs_review: s.review, review: s.review }[status] || s.neutral;
  const label = { needs_review: 'waiting for moderator', review: 'moderator review' }[status] || status;
  return <span className={`${s.badge} ${cls}`}>{label}</span>;
}

export default function ReviewBanner({ result }) {
  if (!result?.submission_id) return null;
  const review = result.review || {};
  return (
    <div className={s.card}>
      <div className={s.row} style={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          Panel total <b>{review.aggregate?.total ?? result.total_score}/40</b>{' '}
          <VerdictBadge status={result.review_status || result.status} />{' '}
          {result.nft_minted && <span className={s.subtle}>credential issued ({result.blockchain_tx?.chain === 'mock' ? 'MOCK CHAIN' : 'Sui'})</span>}
        </div>
        <Link className={s.button} to={`/review/${result.submission_id}`}>View review trace</Link>
      </div>
      {review.decision?.reasons && <p className={s.subtle}>Why: {review.decision.reasons.join('; ')}</p>}
      {review.feedback && <p>{review.feedback}</p>}
    </div>
  );
}
