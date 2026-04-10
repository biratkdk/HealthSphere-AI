import React, { Component, Suspense, lazy, useEffect, useState } from "react";
import { NavLink, Route, Routes, matchPath, useLocation } from "react-router-dom";
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
const ImagingWorkbench = lazy(() => import("./pages/ImagingWorkbench"));
const Notifications = lazy(() => import("./pages/Notifications"));
const Patients = lazy(() => import("./pages/Patients"));
const PatientDetails = lazy(() => import("./pages/PatientDetails"));
const Population = lazy(() => import("./pages/Population"));
const Profile = lazy(() => import("./pages/Profile"));
const Reports = lazy(() => import("./pages/Reports"));

const mobileRoutes = [
  { to: "/", label: "Operations", shortLabel: "Ops", end: true },
  { to: "/population", label: "Population", shortLabel: "Units" },
  { to: "/patients", label: "Patients", shortLabel: "Patients" },
  { to: "/imaging", label: "Imaging", shortLabel: "Imaging" },
  { to: "/reports", label: "Reports", shortLabel: "Reports" },
  { to: "/notifications", label: "Inbox", shortLabel: "Inbox" },
  { to: "/profile", label: "Profile", shortLabel: "Profile" },
];

const navigationGroups = [
  {
    label: "Clinical command",
    items: [
      {
        to: "/",
        label: "Operations",
        shortLabel: "Ops",
        navCode: "01",
        description: "Care-unit load, active alerts, and queue pressure.",
        end: true,
      },
      {
        to: "/population",
        label: "Population",
        shortLabel: "Population",
        navCode: "02",
        description: "Hot patients, overdue work, and unit pressure.",
      },
      {
        to: "/patients",
        label: "Patients",
        shortLabel: "Patients",
        navCode: "03",
        description: "Patient roster and mission-control entry points.",
      },
    ],
  },
  {
    label: "Workflow control",
    items: [
      {
        to: "/imaging",
        label: "Imaging",
        shortLabel: "Imaging",
        navCode: "04",
        description: "Study review, escalation, and sign-off.",
      },
      {
        to: "/reports",
        label: "Reports",
        shortLabel: "Reports",
        navCode: "05",
        description: "Report queue from intake to release.",
      },
      {
        to: "/notifications",
        label: "Inbox",
        shortLabel: "Inbox",
        navCode: "06",
        description: "Unread events, escalations, and follow-through.",
      },
      {
        to: "/profile",
        label: "Profile",
        shortLabel: "Profile",
        navCode: "07",
        description: "Identity, sessions, and workspace defaults.",
      },
      {
        to: "/admin",
        label: "Admin",
        shortLabel: "Admin",
        navCode: "08",
        description: "Users, invites, and audit history.",
        adminOnly: true,
      },
    ],
  },
];

const getWorkspaceMeta = (pathname, unreadCount, user) => {
  const unreadLabel = unreadCount > 0 ? `${unreadCount} unread inbox` : "Inbox clear";
  const orgLabel = user?.organization_name ? `Org: ${user.organization_name}` : "Organization scoped";

  if (matchPath("/patients/:patientId", pathname)) {
    return {
      eyebrow: "Patient operations",
      title: "Patient Mission Control",
      summary: "One patient. Current changes, drivers, and next steps.",
      chips: [
        { label: "Live", tone: "low" },
        { label: "Next actions", tone: "medium" },
        { label: unreadLabel, tone: unreadCount > 0 ? "high" : "low" },
      ],
    };
  }

  if (pathname === "/patients") {
    return {
      eyebrow: "Patient command",
      title: "Mission-Control Roster",
      summary: "Find the right patient fast and open the live workspace.",
      chips: [
        { label: "Roster ready", tone: "low" },
        { label: unreadLabel, tone: unreadCount > 0 ? "medium" : "low" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/population") {
    return {
      eyebrow: "Population operations",
      title: "Care-Unit Command Board",
      summary: "Track unit pressure, overdue work, alerts, and imaging demand.",
      chips: [
        { label: "Unit pressure", tone: "medium" },
        { label: unreadLabel, tone: unreadCount > 0 ? "medium" : "low" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/imaging") {
    return {
      eyebrow: "Imaging operations",
      title: "Imaging Triage Workbench",
      summary: "Review studies, escalate when needed, and sign off in one lane.",
      chips: [
        { label: "Review lane", tone: "medium" },
        { label: "Reports linked", tone: "low" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/reports") {
    return {
      eyebrow: "Report orchestration",
      title: "Imaging and Report Queue",
      summary: "Queue, track, and release report packages.",
      chips: [
        { label: "Queue active", tone: "medium" },
        { label: "Imaging linked", tone: "low" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/notifications") {
    return {
      eyebrow: "Clinical inbox",
      title: "Alerts and Notifications",
      summary: "Unread alerts, completions, and follow-up.",
      chips: [
        { label: unreadLabel, tone: unreadCount > 0 ? "high" : "low" },
        { label: "Actionable", tone: "medium" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/profile") {
    return {
      eyebrow: "Operator identity",
      title: "Profile and Preferences",
      summary: "Manage identity, sessions, and workspace defaults.",
      chips: [
        { label: user?.role || "role-scoped", tone: "low" },
        { label: user?.auth_provider || "password auth", tone: "medium" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  if (pathname === "/admin") {
    return {
      eyebrow: "Governance and control",
      title: "Admin Console",
      summary: "Access control, invites, and audit activity.",
      chips: [
        { label: "Audit live", tone: "medium" },
        { label: "Access control", tone: "low" },
        { label: orgLabel, tone: "low" },
      ],
    };
  }

  return {
    eyebrow: "Operations command",
    title: "Clinical Operating System",
    summary: "Patient, workflow, imaging, and reporting state in one view.",
    chips: [
      { label: "Operations live", tone: "low" },
      { label: unreadLabel, tone: unreadCount > 0 ? "medium" : "low" },
      { label: orgLabel, tone: "low" },
    ],
  };
};

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
  const workspaceMeta = getWorkspaceMeta(location.pathname, unreadCount, user);
  const visibleNavigationGroups = navigationGroups.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.adminOnly || user?.role === "admin"),
  }));

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
    <div className="shell app-shell">
      <aside className="app-sidebar">
        <section className="sidebar-brand-card">
          <div className="sidebar-brand-mark">HS</div>
          <div className="sidebar-brand-copy">
            <p className="sidebar-kicker">Clinical operating system</p>
            <h1>HealthSphere AI</h1>
            <p>Patient control, imaging, reporting, and audit in one workspace.</p>
          </div>
        </section>

        <div className="sidebar-nav-stack">
          {visibleNavigationGroups.map((group) => (
            <section key={group.label} className="sidebar-nav-group">
              <p className="sidebar-group-label">{group.label}</p>
              <nav className="sidebar-nav" aria-label={group.label}>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `sidebar-nav-link${isActive ? " active" : ""}`}
                  >
                    <span className="sidebar-nav-code">{item.navCode}</span>
                    <span className="sidebar-nav-copy">
                      <strong>{item.label}</strong>
                      <small>{item.description}</small>
                    </span>
                    {item.to === "/notifications" && unreadCount > 0 ? (
                      <span className="sidebar-nav-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
                    ) : null}
                  </NavLink>
                ))}
              </nav>
            </section>
          ))}
        </div>

        <section className="sidebar-status-card">
          <p className="sidebar-group-label">Platform posture</p>
          <strong>Shared clinical control</strong>
          <p>
            Patient signals, task ownership, handoffs, imaging review, reports, and audit events stay inside one
            operating layer.
          </p>
          <div className="sidebar-status-pills">
            <span className="tone tone-low">Patients</span>
            <span className="tone tone-medium">Workflow</span>
            <span className="tone tone-low">Governance</span>
          </div>
        </section>
      </aside>

      <div className="workspace-shell">
        <header className="workspace-header">
          <div className="workspace-header-copy">
            <p className="workspace-kicker">{workspaceMeta.eyebrow}</p>
            <h1>{workspaceMeta.title}</h1>
            <p>{workspaceMeta.summary}</p>
            <div className="workspace-chip-row">
              {workspaceMeta.chips.map((chip) => (
                <span key={chip.label} className={`tone tone-${chip.tone}`}>
                  {chip.label}
                </span>
              ))}
            </div>
          </div>

          <div className="workspace-header-actions">
            <div className="user-chip workspace-user-chip">
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

        <main className="app-main workspace-main">
          <RouteErrorBoundary>
            <Suspense fallback={<section className="panel loading-panel"><div className="spinner" /><p>Loading workspace&hellip;</p></section>}>
              <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/population" element={<Population />} />
              <Route path="/patients" element={<Patients />} />
              <Route path="/patients/:patientId" element={<PatientDetails />} />
              <Route path="/imaging" element={<ImagingWorkbench />} />
              <Route path="/reports" element={<Reports />} />
                <Route path="/notifications" element={<Notifications />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="/auth/callback" element={<AuthCallback />} />
              </Routes>
            </Suspense>
          </RouteErrorBoundary>
        </main>
      </div>

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
