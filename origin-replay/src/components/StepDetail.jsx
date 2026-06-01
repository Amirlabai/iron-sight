export default function StepDetail({ step, storedOrigin, replayOrigin, match }) {
  if (!step) {
    return (
      <div className="step-detail empty">
        <p className="muted">Step details appear here.</p>
      </div>
    );
  }

  const isFinal = step.id === 'final';

  return (
    <div className="step-detail">
      <h3>{step.title}</h3>
      <p className="summary">{step.summary}</p>

      {Object.keys(step.decision || {}).length > 0 && (
        <div className="decision-block">
          <h4>Decision</h4>
          <pre>{JSON.stringify(step.decision, null, 2)}</pre>
        </div>
      )}

      {isFinal && storedOrigin != null && (
        <div className={`match-block ${match ? 'match-ok' : 'match-diff'}`}>
          <h4>Archive comparison</h4>
          <p>
            Stored origin: <code>{storedOrigin ?? '—'}</code>
          </p>
          <p>
            Replay origin: <code>{replayOrigin ?? '—'}</code>
          </p>
          <p>{match ? 'Replay matches stored archive.' : 'Replay differs from stored archive.'}</p>
        </div>
      )}
    </div>
  );
}
