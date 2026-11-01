import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../utils/api';
import { VerdictBadge } from '../components/ReviewBanner';
import s from './v2.module.css';

const JUDGES = ['synopsis', 'logic', 'hypothesis', 'bias'];
const DETAIL = {
  synopsis: ['key_points_missed', 'Key points missed'],
  logic: ['inconsistencies', 'Inconsistencies'],
  hypothesis: ['counterpoints', 'Counterpoints'],
  bias: ['detected_biases', 'Detected biases'],
};

// Node-by-node trace of one review: guard -> dedupe -> evidence -> 4 judges -> aggregate -> gate -> ...
export default function ReviewTracePage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`/review/${id}`).then((r) => setData(r.data)).catch((e) => setError(e.response?.data?.detail || e.message));
  }, [id]);

  if (error) return <div className={s.page}>Error: {error}</div>;
  if (!data) return <div className={s.page}>Loading review trace...</div>;
  const agg = data.aggregate || {};

  return (
    <div className={s.page}>
      <h1 className={s.title}>Review trace: submission #{data.submission_id}</h1>
      <p className={s.subtle}>thread <code>{data.thread_id}</code> <VerdictBadge status={data.status} /></p>

      <div className={s.card}>
        <h3>Submission (PII masked)</h3>
        <p>{data.text}</p>
        <p className={s.subtle}>
          Guard: safe={String(data.guard?.is_safe)}; injection: {data.guard?.injection?.join('; ') || 'none'};
          PII masked: {data.guard?.pii_masked?.join(', ') || 'none'}. Duplicate check: closest #{data.duplicate?.of ?? '-'} at
          similarity {data.duplicate?.similarity}{data.duplicate?.is_duplicate ? ' (NEAR-DUPLICATE)' : ''}.
        </p>
      </div>

      <div className={s.card}>
        <h3>Graph progress</h3>
        {data.events.map((e, i) => (
          <div key={i} className={s.node}>
            <span className={s.nodeName}>{e.node}</span><span>{e.summary}</span>
            <span className={s.subtle} style={{ marginLeft: 'auto' }}>{e.ms} ms</span>
          </div>
        ))}
        {data.waiting_for?.length > 0 && <p className={s.demoBanner}>Paused before: {data.waiting_for.join(', ')}. A moderator decides in the <Link to="/moderation">queue</Link>.</p>}
      </div>

      <h3>The panel: four judges side by side</h3>
      <div className={s.row}>
        {JUDGES.map((name) => {
          const j = data.judges[name];
          if (!j) return null;
          const [key, label] = DETAIL[name];
          return (
            <div key={name} className={`${s.card} ${s.col}`}>
              <div className={s.row} style={{ justifyContent: 'space-between' }}>
                <b style={{ textTransform: 'capitalize' }}>{name}</b><span className={s.subtle}>{j.mode}</span>
              </div>
              <div className={s.score}>{j.score}/10</div>
              <div className={s.bar}><div className={s.barFill} style={{ width: `${j.score * 10}%` }} /></div>
              <p>{j.rationale}</p>
              {j.flags?.map((f, i) => (
                <p key={i}>
                  <span className={`${s.badge} ${f.severity === 'critical' ? s.reject : s.review}`}>{f.severity}</span>{' '}
                  {f.text} <b>{f.evidence_ids?.length ? `[${f.evidence_ids.join(', ')}]` : '(uncited)'}</b>
                </p>
              ))}
              {j[key]?.length > 0 && (<><p className={s.subtle}>{label}</p><ul>{j[key].map((x, i) => <li key={i}>{x}</li>)}</ul></>)}
            </div>
          );
        })}
      </div>

      <div className={s.card}>
        <h3>Gate decision (code, not the model)</h3>
        <p>Total <b>{agg.total}/{agg.max_total}</b>, disagreement (spread of normalised scores) <b>{agg.disagreement}</b></p>
        <p><VerdictBadge status={data.decision?.verdict} /> decided by <b>{data.decision?.decided_by}</b>: {data.decision?.reasons?.join('; ')}</p>
        <p className={s.subtle}>Rules: unsafe → reject; total &lt; 26 → reject; injection / near-duplicate / disagreement &gt; 0.4 → moderator; total ≥ 30 with no uncited critical flag → accept; otherwise moderator.</p>
        {data.moderation && <p>Moderator: {data.moderation.choice} {data.moderation.adjusted && `(adjusted ${JSON.stringify(data.moderation.adjusted)})`} {data.moderation.note}</p>}
        {data.credential && <p>Credential: {data.credential.rank} · {data.credential.chain === 'mock' ? 'MOCK CHAIN' : 'Sui'} digest <code>{data.credential.digest}</code></p>}
        {data.reputation && <p>Reputation +{data.reputation.points_added} (now {data.reputation.points})</p>}
      </div>

      {data.feedback && <div className={s.card}><h3>Feedback to the contributor</h3><p>{data.feedback}</p></div>}

      <div className={s.card}>
        <h3>Evidence the judges saw</h3>
        {data.evidence.map((e) => (
          <details key={e.evidence_id}><summary><b>{e.evidence_id}</b> {e.title} <span className={s.subtle}>rerank {e.score}</span></summary>
            <div className={s.evidence}>{e.text}</div></details>
        ))}
      </div>
    </div>
  );
}
