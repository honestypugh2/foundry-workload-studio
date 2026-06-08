import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { RunResponse } from '../api/types';
import RequestEditor from '../components/RequestEditor';
import TracePanel from '../components/TracePanel';
import WorkflowPanel from '../components/WorkflowPanel';

export default function UseCasePage() {
  const { slug = '' } = useParams();
  const [run, setRun] = useState<RunResponse | null>(null);

  const detail = useQuery({
    queryKey: ['usecase', slug],
    queryFn: () => api.getUseCase(slug),
    enabled: Boolean(slug),
  });

  const mutation = useMutation({
    mutationFn: (payload: unknown) => api.runUseCase(slug, payload),
    onSuccess: (data) => setRun(data),
  });

  // Clear any previous run output (and any in-flight mutation state) when the
  // user switches to a different use case so stale results don't bleed across
  // pages.
  useEffect(() => {
    setRun(null);
    mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  if (detail.isLoading) {
    return <div className="page">Loading use case…</div>;
  }
  if (detail.error || !detail.data) {
    return (
      <div className="page error">
        Could not load use case <code>{slug}</code>.
      </div>
    );
  }

  const uc = detail.data;
  const activeStepNames = run?.trace.steps.map((s) => s.name) ?? [];

  return (
    <div className="page usecase-grid">
      <header className="page-header">
        <div className="card-cat">{uc.category}</div>
        <h1>{uc.name}</h1>
        <p className="lead">{uc.description}</p>
        <div className="card-services">
          {uc.azure_services.map((s) => (
            <span key={s} className="chip">
              {s}
            </span>
          ))}
        </div>
      </header>

      <div className="usecase-cols">
        <div className="usecase-col">
          <RequestEditor
            key={slug}
            initial={uc.sample_input}
            busy={mutation.isPending}
            onSubmit={(payload) => mutation.mutate(payload)}
            onReset={() => {
              setRun(null);
              mutation.reset();
            }}
          />
          {mutation.error && (
            <div className="editor-error">
              Run failed: {(mutation.error as Error).message}
            </div>
          )}

          <section className="result-panel">
            <div className="panel-title">Result</div>
            {run ? (
              <pre className="result-json">
                {JSON.stringify(run.result, null, 2)}
              </pre>
            ) : (
              <p className="panel-muted">Run the use case to see the agent response.</p>
            )}
          </section>
        </div>

        <div className="usecase-col">
          <WorkflowPanel
            workflow={run?.trace.workflow ?? uc.workflow}
            activeStepNames={activeStepNames}
          />
          <TracePanel trace={run?.trace ?? null} />
        </div>
      </div>
    </div>
  );
}
