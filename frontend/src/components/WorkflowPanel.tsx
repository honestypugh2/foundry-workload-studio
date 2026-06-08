import type { Workflow } from '../api/types';

interface Props {
  workflow: Workflow | null | undefined;
  activeStepNames?: string[];
}

/**
 * Lightweight workflow visualiser. Renders nodes left-to-right and lists the
 * declared edges. Highlights nodes that match observed step names so the
 * panel doubles as a "where am I" indicator after a run.
 */
export default function WorkflowPanel({ workflow, activeStepNames = [] }: Props) {
  if (!workflow) {
    return (
      <section className="workflow-panel">
        <div className="panel-title">Workflow</div>
        <p className="panel-muted">No workflow declared for this use case.</p>
      </section>
    );
  }

  const active = new Set(activeStepNames);

  return (
    <section className="workflow-panel">
      <div className="panel-title">Workflow</div>

      <div className="workflow-flow">
        {workflow.nodes.map((node, i) => (
          <div key={node} className="workflow-node-wrap">
            <div className={'workflow-node' + (active.has(node) ? ' active' : '')}>
              {node}
            </div>
            {i < workflow.nodes.length - 1 && (
              <span className="workflow-arrow" aria-hidden>
                →
              </span>
            )}
          </div>
        ))}
      </div>

      {workflow.edges.length > 0 && (
        <details className="workflow-edges">
          <summary>Edges ({workflow.edges.length})</summary>
          <ul>
            {workflow.edges.map((edge, i) => (
              <li key={i}>
                <code>{edge.source}</code> → <code>{edge.target}</code>
                {edge.label && <em> ({edge.label})</em>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
