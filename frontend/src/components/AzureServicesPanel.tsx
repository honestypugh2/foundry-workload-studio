import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ServiceState } from '../api/types';

const STATE_LABEL: Record<ServiceState, string> = {
  live: 'LIVE',
  configured: 'configured',
  unconfigured: 'offline',
  error: 'error',
};

export default function AzureServicesPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['azure-services'],
    queryFn: api.listAzureServices,
    staleTime: 5 * 60_000,
  });
  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: api.getStatus,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const stateById = new Map<string, ServiceState>(
    status?.services.map((s) => [s.id, s.state]) ?? [],
  );
  const detailById = new Map<string, string>(
    status?.services
      .filter((s): s is typeof s & { detail: string } => Boolean(s.detail))
      .map((s) => [s.id, s.detail]) ?? [],
  );

  return (
    <section className="azure-panel" aria-label="Azure services">
      <div className="panel-title">Azure services</div>
      {isLoading && <div className="panel-muted">Loading…</div>}
      {error && <div className="panel-muted error">Unavailable</div>}
      <ul className="azure-list">
        {data?.services.map((svc) => {
          const state = stateById.get(svc.id) ?? 'unconfigured';
          return (
            <li key={svc.id} className="azure-item">
              <a
                className="azure-item-name"
                href={svc.docs_url}
                target="_blank"
                rel="noreferrer"
                title={detailById.get(svc.id) ?? svc.role}
              >
                {svc.name}
              </a>
              <span className={`azure-item-state state-${state}`}>
                {STATE_LABEL[state]}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
