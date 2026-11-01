import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import s from '../pages/v2.module.css';

// v2: every case has an evidence pack. Contributors read it; the AI judges are given the same documents.
export default function EvidencePack({ caseId }) {
  const [evidence, setEvidence] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`/cases/${caseId}`)
      .then((res) => setEvidence(res.data.evidence))
      .catch((err) => setError(err.message));
  }, [caseId]);

  if (error) return <div className={s.card}>Could not load the evidence pack: {error}</div>;
  return (
    <div className={s.page} style={{ marginTop: 20 }}>
      <h2>Evidence pack</h2>
      <p className={s.subtle}>Cite evidence ids like [E3] in your analysis. The review panel checks claims against these documents.</p>
      {evidence.map((e) => (
        <details key={e.evidence_id} className={s.card}>
          <summary><b>{e.evidence_id}</b> {e.title} <span className={s.subtle}>({e.doc_type}, {e.date})</span></summary>
          <div className={s.evidence}>{e.body}</div>
        </details>
      ))}
    </div>
  );
}
