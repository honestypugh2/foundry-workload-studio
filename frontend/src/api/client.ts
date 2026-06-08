import type {
  AzureServicesResponse,
  RunResponse,
  StatusResponse,
  UseCaseDetail,
  UseCaseSummary,
} from './types';

const BASE = '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listUseCases: () => request<UseCaseSummary[]>('/api/usecases'),
  getUseCase: (slug: string) => request<UseCaseDetail>(`/api/usecases/${slug}`),
  runUseCase: (slug: string, payload: unknown) =>
    request<RunResponse>(`/api/usecases/${slug}/run`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listAzureServices: () => request<AzureServicesResponse>('/api/azure-services'),
  getStatus: () => request<StatusResponse>('/api/status'),
};
