import type { Trace } from '../api/types';

interface Props {
  trace: Trace | null;
}

function fmt(n: number) {
  return n >= 10 ? n.toFixed(0) : n.toFixed(2);
}

export default function TracePanel({ trace }: Props) {
  if (!trace) {
    return (
      <section className="trace-panel">
        <div className="panel-title">Trace &amp; debug</div>
        <p className="panel-muted">Run the use case to populate the trace.</p>
      </section>
    );
  }

  const total = trace.duration_ms || 1;
  return (
    <section className="trace-panel">
      <header className="trace-header">
        <div className="panel-title">Trace &amp; debug</div>
        <div className="trace-meta">
          <span className="badge">run {trace.run_id.slice(0, 8)}</span>
          <span className="badge">{fmt(trace.duration_ms)} ms</span>
          <span className="badge">{trace.steps.length} steps</span>
        </div>
      </header>

      <div className="trace-services">
        {trace.azure_services_invoked.map((id) => (
          <span key={id} className="chip">
            {id}
          </span>
        ))}
      </div>

      <ol className="trace-steps">
        {trace.steps.map((step, i) => {
          const widthPct = Math.max(2, (step.duration_ms / total) * 100);
          return (
            <li key={i} className={`trace-step status-${step.status}`}>
              <div className="trace-step-row">
                <span className="trace-step-name">{step.name}</span>
                <span className="trace-step-dur">{fmt(step.duration_ms)} ms</span>
              </div>
              <div className="trace-bar-track">
                <div className="trace-bar" style={{ width: `${widthPct}%` }} />
              </div>
              {Object.keys(step.attributes).length > 0 && (
                <ul className="trace-attrs">
                  {Object.entries(step.attributes).map(([k, v]) => (
                    <li key={k}>
                      <span className="attr-k">{k}</span>
                      <span className="attr-v">{String(v)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
