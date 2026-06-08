import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export default function ModeBanner() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['status'],
    queryFn: api.getStatus,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="mode-banner loading" role="status">
        Checking Azure connectivity…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mode-banner error" role="alert">
        Gateway unreachable
      </div>
    );
  }

  const isLive = data.mode === 'live';
  const foundry = data.services.find((s) => s.id === 'foundry');
  const search = data.services.find((s) => s.id === 'ai-search');

  return (
    <div
      className={`mode-banner ${isLive ? 'live' : 'offline'}`}
      role="status"
      title={foundry?.detail ?? ''}
    >
      <span className={`mode-dot ${isLive ? 'live' : 'offline'}`} aria-hidden />
      <span className="mode-label">
        {isLive ? 'LIVE — Azure' : 'OFFLINE — local stubs'}
      </span>
      <span className="mode-env">env: {data.environment}</span>
      <span className="mode-sep">·</span>
      <span className="mode-meta">
        Foundry:{' '}
        <strong className={`state-${foundry?.state ?? 'unconfigured'}`}>
          {foundry?.state ?? 'unknown'}
        </strong>
      </span>
      <span className="mode-meta">
        AI Search:{' '}
        <strong className={`state-${search?.state ?? 'unconfigured'}`}>
          {search?.state ?? 'unknown'}
        </strong>
      </span>
      <span className="mode-meta">
        model: <code>{data.foundry_model_deployment}</code>
      </span>
    </div>
  );
}
