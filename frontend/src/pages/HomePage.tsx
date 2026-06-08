import type { UseCaseSummary } from '../api/types';
import { Link } from 'react-router-dom';

interface Props {
  useCases: UseCaseSummary[];
}

export default function HomePage({ useCases }: Props) {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Foundry Workload Studio</h1>
        <p className="lead">
          A unified explorer for every Foundry-powered use case in this repo.
          Pick a use case, send a request, and watch the agent steps and
          backing Azure services light up in real time.
        </p>
      </header>

      <section className="card-grid">
        {useCases.map((uc) => (
          <Link key={uc.slug} to={`/u/${uc.slug}`} className="card">
            <div className="card-cat">{uc.category}</div>
            <div className="card-title">{uc.name}</div>
            <p className="card-desc">{uc.description}</p>
            <div className="card-services">
              {uc.azure_services.map((s) => (
                <span key={s} className="chip">
                  {s}
                </span>
              ))}
            </div>
          </Link>
        ))}
        {useCases.length === 0 && (
          <div className="empty">
            No use cases registered. Start the gateway with{' '}
            <code>uvicorn src.gateway.api:app --reload</code>.
          </div>
        )}
      </section>
    </div>
  );
}
