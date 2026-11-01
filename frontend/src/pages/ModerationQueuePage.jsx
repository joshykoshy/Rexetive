import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import s from './v2.module.css';

const JUDGES = ['synopsis', 'logic', 'hypothesis', 'bias'];

function QueueItem({ item, onDone }) {
  const [note, setNote] = useState('');
  const [scores, setScores] = useState(item.scores || {});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const decide = async (decision) => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${item.id}/resume`, { decision, note, scores: decision === 'adjust' ? scores : {} });
      onDone();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.card}>
      <div className={s.row} style={{ justifyContent: 'space-between' }}>
        <b>#{item.id} · case {item.case_id} · {item.mode} · by {item.display_name}</b>
        <span>total {item.total_score}/40 · spread {item.disagreement}</span>
      </div>
      <p className={s.subtle}>Why it's here: {item.reasons.join('; ')}</p>
      <p>{item.text.length > 400 ? `${item.text.slice(0, 400)}...` : item.text}</p>
      {item.resumable ? (
        <>
          <div className={s.row}>
            {JUDGES.map((j) => (
              <label key={j} className={s.subtle}>{j}{' '}
                <input type="number" min="0" max="10" className={s.input} style={{ width: 70 }}
                  value={scores[j] ?? ''} onChange={(e) => setScores({ ...scores, [j]: Number(e.target.value) })} />
              </label>
            ))}
          </div>
          <input className={s.input} placeholder="Note (logged with the AI's original verdict)" value={note}
            onChange={(e) => setNote(e.target.value)} style={{ margin: '8px 0' }} />
          <div className={s.row}>
            <button className={s.button} disabled={busy} onClick={() => decide('approve')}>Approve</button>
            <button className={`${s.button} ${s.danger}`} disabled={busy} onClick={() => decide('reject')}>Reject</button>
            <button className={`${s.button} ${s.secondary}`} disabled={busy} onClick={() => decide('adjust')}>Adjust scores</button>
            <Link to={`/review/${item.id}`} className={s.subtle}>open trace</Link>
          </div>
        </>
      ) : <p className={s.subtle}>Seeded example without a live review thread (analytics data only).</p>}
      {error && <p style={{ color: '#ff9b9b' }}>{error}</p>}
    </div>
  );
}

export default function ModerationQueuePage() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [liveOnly, setLiveOnly] = useState(true);

  const load = () => api.get('/moderation/queue').then((r) => setItems(r.data)).catch((e) => setError(e.response?.data?.detail || e.message));
  useEffect(() => { load(); }, []);

  if (error) return <div className={s.page}>Error: {error}</div>;
  if (!items) return <div className={s.page}>Loading queue...</div>;
  const shown = liveOnly ? items.filter((i) => i.resumable) : items;
  return (
    <div className={s.page}>
      <h1 className={s.title}>Moderation queue</h1>
      <p className={s.subtle}>Grey-zone items the policy gate would not decide alone. Each decision resumes the paused LangGraph run
        and is logged next to the AI's original verdict; overrides become new eval cases.</p>
      <label className={s.subtle}><input type="checkbox" checked={liveOnly} onChange={(e) => setLiveOnly(e.target.checked)} /> live reviews only</label>
      {shown.length === 0 && <div className={s.card}>Nothing waiting. Submit a borderline analysis to see one here.</div>}
      {shown.map((item) => <QueueItem key={item.id} item={item} onDone={load} />)}
    </div>
  );
}
