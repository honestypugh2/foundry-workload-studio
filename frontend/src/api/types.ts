// API types mirror the gateway's Pydantic models. Keep these in sync with
// src/gateway/api.py and src/gateway/tracing.py.

export interface UseCaseSummary {
  slug: string;
  name: string;
  description: string;
  category: string;
  request_kind: 'chat' | 'complaint' | 'maintenance' | string;
  sample_input: Record<string, unknown>;
  azure_services: string[];
}

export interface WorkflowEdge {
  source: string;
  target: string;
  label?: string | null;
}

export interface Workflow {
  nodes: string[];
  edges: WorkflowEdge[];
}

export interface UseCaseDetail extends UseCaseSummary {
  workflow: Workflow;
}

export interface TraceStep {
  name: string;
  status: 'ok' | 'warning' | 'error' | string;
  started_at: string;
  duration_ms: number;
  attributes: Record<string, string | number | boolean>;
}

export interface Trace {
  run_id: string;
  use_case: string;
  started_at: string;
  duration_ms: number;
  steps: TraceStep[];
  azure_services_invoked: string[];
  workflow: Workflow | null;
}

export interface RunResponse {
  use_case: string;
  result: Record<string, unknown>;
  trace: Trace;
}

export interface AzureService {
  id: string;
  name: string;
  category: string;
  role: string;
  docs_url: string;
}

export interface AzureServicesResponse {
  services: AzureService[];
}

export type ServiceState = 'live' | 'configured' | 'unconfigured' | 'error';

export interface ServiceStatus {
  id: string;
  state: ServiceState;
  endpoint?: string | null;
  detail?: string | null;
}

export interface StatusResponse {
  environment: string;
  mode: 'offline' | 'live';
  foundry_model_deployment: string;
  services: ServiceStatus[];
}
