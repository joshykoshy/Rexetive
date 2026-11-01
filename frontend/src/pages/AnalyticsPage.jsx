import React, { useState } from 'react';
import api from '../utils/api';
import s from './v2.module.css';

const EXAMPLES = ['What is the acceptance rate per case?', 'Who are the top contributors?',
  'What is the average score per judge?', 'Which submissions are waiting for review?'];
const ATTACKS = ['DROP TABLE users', 'SELECT * FROM users; DROP TABLE users; --', 'SELECT * FROM moderation_log',
  "ATTACH DATABASE 'x.db' AS x"];

// Natural language -> SQL (fast model, or templates offline) -> sqlglot guard -> read-only DB.
export default function AnalyticsPage() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [sql, setSql] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async (body) => {
    setBusy(true);
    try {
      const r = await api.post('/analytics/ask', body);
      setResult(r.data);
    } catch (e) {
      setResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setBusy(false);
    }
  };

  const blocked = result?.guard && !result.guard.ok;
  return (
    <div className={s.page}>
      <h1 className={s.title}>Moderator analytics</h1>
      <p className={s.subtle}>Ask in plain English. The generated SQL is validated (one SELECT, allowlisted tables only, LIMIT 200)
        and run on a read-only connection. You can also type SQL: it goes through the same guard.</p>
      <div className={s.card}>
        <input className={s.input} value={question} onChange={(e) => setQuestion(e.target.value)} />
        <div className={s.row} style={{ margin: '8px 0' }}>
          <button className={s.button} disabled={busy} onClick={() => run({ question })}>Ask</button>
          {EXAMPLES.map((q) => <button key={q} className={`${s.button} ${s.secondary}`} onClick={() => setQuestion(q)}>{q}</button>)}
        </div>
      </div>
      <div className={s.card}>
        <textarea className={s.textarea} placeholder="...or type SQL" value={sql} onChange={(e) => setSql(e.target.value)} />
        <div className={s.row} style={{ marginTop: 8 }}>
          <button className={s.button} disabled={busy || !sql} onClick={() => run({ sql })}>Run SQL</button>
          {ATTACKS.map((a) => <button key={a} className={`${s.button} ${s.danger}`} onClick={() => setSql(a)}>try: {a.slice(0, 28)}</button>)}
        </div>
      </div>
      {result && (
        <div className={s.card}>
          {result.sql && <><p className={s.subtle}>SQL ({result.source}){result.explanation && `: ${result.explanation}`}</p>
            <div className={`${s.code} ${blocked ? s.blocked : ''}`}>{result.safe_sql || result.sql}</div></>}
          {result.guard && <p>Guard: {result.guard.ok ? <span className={`${s.badge} ${s.accept}`}>allowed</span>
            : <span className={`${s.badge} ${s.reject}`}>BLOCKED: {result.guard.reason}</span>}</p>}
          {result.error && <p style={{ color: '#ff9b9b' }}>{result.error}</p>}
          {result.columns?.length > 0 && (
            <table className={s.table}>
              <thead><tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{result.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{String(v)}</td>)}</tr>)}</tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
