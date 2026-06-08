import { NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';
import AzureServicesPanel from './components/AzureServicesPanel';
import ModeBanner from './components/ModeBanner';
import HomePage from './pages/HomePage';
import UseCasePage from './pages/UseCasePage';

export default function App() {
  const location = useLocation();
  const activeSlug = location.pathname.startsWith('/u/')
    ? location.pathname.split('/')[2]
    : null;

  const { data: useCases, isLoading, error } = useQuery({
    queryKey: ['usecases'],
    queryFn: api.listUseCases,
  });

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">F</div>
          <div>
            <div className="brand-title">Foundry Workload Studio</div>
            <div className="brand-sub">Explorer</div>
          </div>
        </div>

        <nav className="nav">
          <NavLink
            to="/"
            className={({ isActive }) =>
              'nav-link home' + (isActive ? ' active' : '')
            }
          >
            <div className="nav-link-name">Overview</div>
            <div className="nav-link-cat">Architecture &amp; status</div>
          </NavLink>

          <div className="nav-section">Use cases</div>
          {isLoading && <div className="nav-empty">Loading…</div>}
          {error && <div className="nav-empty error">Gateway unavailable</div>}
          {useCases?.map((uc) => (
            <NavLink
              key={uc.slug}
              to={`/u/${uc.slug}`}
              className={({ isActive }) =>
                'nav-link' + (isActive || activeSlug === uc.slug ? ' active' : '')
              }
            >
              <div className="nav-link-name">{uc.name}</div>
              <div className="nav-link-cat">{uc.category}</div>
            </NavLink>
          ))}
        </nav>

        <AzureServicesPanel />
      </aside>

      <main className="main">
        <ModeBanner />
        <Routes>
          <Route path="/" element={<HomePage useCases={useCases ?? []} />} />
          <Route path="/u/:slug" element={<UseCasePage />} />
        </Routes>
      </main>
    </div>
  );
}
