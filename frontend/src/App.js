import React, { Component, Suspense, lazy, useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import useSWR from "swr";

class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("Route render error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="panel error-panel">
          <strong className="error-text">Something went wrong</strong>
          <p>This page encountered an unexpected error. Please refresh or navigate away.</p>
          <button
            className="secondary-button small-button"
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}

import PublicLanding from "./components/PublicLanding";
import { useAuth } from "./context/AuthContext";
import AuthCallback from "./pages/AuthCallback";

const Admin = lazy(() => import("./pages/Admin"));
const Home = lazy(() => import("./pages/Home"));
const Notifications = lazy(() => import("./pages/Notifications"));
const Patients = lazy(() => import("./pages/Patients"));
const PatientDetails = lazy(() => import("./pages/PatientDetails"));
const Profile = lazy(() => import("./pages/Profile"));
const Reports = lazy(() => import("./pages/Reports"));

const mobileRoutes = [
  { to: "/", label: "Operations", shortLabel: "Ops", end: true },
  { to: "/patients", label: "Patients", shortLabel: "Patients" },
  { to: "/reports", label: "Reports", shortLabel: "Reports" },
  { to: "/notifications", label: "Inbox", shortLabel: "Inbox" },
  { to: "/profile", label: "Profile", shortLabel: "Profile" },
];

const useTheme = () => {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("hs-theme") || "light";
    } catch {
      return "light";
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("hs-theme", theme);
    } catch { /* */ }
  }, [theme]);

  return [theme, setTheme];
};

const App = () => {
  const location = useLocation();
  const { user, loading, isAuthenticated, logout } = useAuth();
  const [theme, setTheme] = useTheme();

  const { data: analytics } = useSWR(isAuthenticated ? ["analytics"] : null);
  const unreadCount = analytics?.unread_notifications || 0;

  const initials = (user?.full_name || "HS")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  if (loading && location.pathname !== "/auth/callback") {
    return (
      <div className="shell login-shell">
        <section className="panel loading-panel">
          <div className="spinner" />
          <p>Verifying session&hellip;</p>
        </section>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="shell guest-shell">
        <Routes>
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="*" element={<PublicLanding theme={theme} setTheme={setTheme} />} />
        </Routes>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="app-header">
        <div className="brand-block">
          <p className="eyebrow">Clinical intelligence platform</p>
          <h1>HealthSphere AI</h1>
          <p className="subtle-copy">Real-time care coordination, predictive monitoring, and operator workflow control.</p>
        </div>
        <div className="header-controls">
          <nav className="nav-links nav-links-primary" aria-label="Primary">
            <NavLink to="/" end>Operations</NavLink>
            <NavLink to="/patients">Patients</NavLink>
            <NavLink to="/reports">Reports</NavLink>
            <div className="nav-badge-wrap">
              <NavLink to="/notifications">Inbox</NavLink>
              {unreadCount > 0 && (
                <span className="nav-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
              )}
            </div>
            <NavLink to="/profile">Profile</NavLink>
            {user?.role === "admin" ? <NavLink to="/admin">Admin</NavLink> : null}
          </nav>

          <div className="user-chip">
            <div className="user-avatar small-avatar">{initials}</div>
            <div>
              <strong>{user?.full_name}</strong>
              <span>{user?.role} &middot; {user?.username}</span>
              <span>{user?.organization_name || user?.preferences?.department || user?.auth_provider}</span>
            </div>
            <button
              className="theme-toggle"
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "Day" : "Night"}
            </button>
            <button className="secondary-button small-button" type="button" onClick={() => void logout()}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <RouteErrorBoundary>
          <Suspense fallback={<section className="panel loading-panel"><div className="spinner" /><p>Loading workspace&hellip;</p></section>}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/patients" element={<Patients />} />
              <Route path="/patients/:patientId" element={<PatientDetails />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
            </Routes>
          </Suspense>
        </RouteErrorBoundary>
      </main>

      <nav className="mobile-tabbar" aria-label="Mobile navigation">
        {mobileRoutes.map((route) => (
          <NavLink key={route.to} to={route.to} end={route.end}>
            <span>{route.shortLabel}</span>
          </NavLink>
        ))}
        {user?.role === "admin" ? (
          <NavLink to="/admin"><span>Admin</span></NavLink>
        ) : null}
      </nav>
    </div>
  );
};

export default App;
