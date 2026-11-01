import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import s from './v2.module.css';

// Shows the latest `python -m evals.run_all` report: calibration, red team, trajectories, retrieval.
export default function EvalsPage() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/evals/latest').then((r) => setReport(r.data)).catch((e) => setError(e.response?.data?.detail || e.message));
  }, []);

  if (error) return <div className={s.page}>{error}</div>;
  if (!report) return <div className={s.page}>Loading eval report...</div>;
  const cal = report.results.calibration || {};
  return (
    <div className={s.page}>
      <h1 className={s.title}>Evals</h1>
      <div className={s.row}>
        {[['verdict accuracy', cal.accuracy?.toFixed(3)], ["Cohen's kappa", cal.kappa?.toFixed(3)],
          ['MAE total /40', cal.mae_total?.toFixed(2)], ['sent to moderator', `${Math.round((cal.to_moderator || 0) * 100)}%`],
          ['critical errors', cal.critical_errors?.length]].map(([k, v]) => (
          <div key={k} className={`${s.card} ${s.col}`}><div className={s.subtle}>{k}</div><div className={s.score}>{v}</div></div>
        ))}
      </div>
      <div className={s.card}><div className={s.markdown}>{report.markdown}</div></div>
    </div>
  );
}
