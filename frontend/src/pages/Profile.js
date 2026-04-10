import React, { useEffect, useState } from "react";
import useSWR from "swr";

import { useAuth } from "../context/AuthContext";
import { getRequestErrorMessage, revokeAllAuthSessions, revokeAuthSession } from "../services/api";

const emptyForm = {
  full_name: "",
  email: "",
  title: "",
  department: "",
  organization: "",
  phone: "",
  location: "",
  bio: "",
  dashboard_view: "operations",
  notification_preference: "critical",
  current_password: "",
  new_password: "",
};

const Profile = () => {
  const { user, updateProfile, busy, error, clearError, logout } = useAuth();
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [sessionActionBusy, setSessionActionBusy] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const {
    data: sessions = [],
    error: sessionsError,
    mutate: mutateSessions,
  } = useSWR(user ? ["authSessions"] : null);

  useEffect(() => {
    if (!user) {
      return;
    }
    setForm({
      full_name: user.full_name || "",
      email: user.email || "",
      title: user.preferences?.title || "",
      department: user.preferences?.department || "",
      organization: user.preferences?.organization || "",
      phone: user.preferences?.phone || "",
      location: user.preferences?.location || "",
      bio: user.preferences?.bio || "",
      dashboard_view: user.preferences?.dashboard_view || "operations",
      notification_preference: user.preferences?.notification_preference || "critical",
      current_password: "",
      new_password: "",
    });
  }, [user]);

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    clearError();

    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, value]) => value !== "")
      );
      await updateProfile(payload);
      setForm((current) => ({ ...current, current_password: "", new_password: "" }));
      setMessage("Profile updated successfully.");
    } catch {
      return;
    }
  };

  if (!user) {
    return <section className="panel">Loading profile...</section>;
  }

  const revokeSingleSession = async (sessionId) => {
    try {
      setSessionActionBusy(true);
      setSessionError("");
      await revokeAuthSession(sessionId);
      mutateSessions((current = []) => current.filter((session) => session.session_id !== sessionId), false);
      setMessage("Session revoked.");
    } catch (requestError) {
      setMessage("");
      setSessionError(getRequestErrorMessage(requestError, "Unable to revoke the session."));
    } finally {
      setSessionActionBusy(false);
    }
  };

  const revokeAllSessions = async () => {
    try {
      setSessionActionBusy(true);
      setSessionError("");
      await revokeAllAuthSessions();
      mutateSessions([], false);
      setMessage("All sessions revoked.");
      await logout();
    } catch (requestError) {
      setMessage("");
      setSessionError(getRequestErrorMessage(requestError, "Unable to revoke all sessions."));
    } finally {
      setSessionActionBusy(false);
    }
  };

  return (
    <div className="page-grid profile-grid">
      <section className="hero-panel profile-hero">
        <div className="profile-identity">
          <div className="profile-avatar">
            {user.full_name
              .split(" ")
              .filter(Boolean)
              .slice(0, 2)
              .map((part) => part[0])
              .join("")
              .toUpperCase()}
          </div>
          <div>
            <p className="eyebrow">Account workspace</p>
            <h2>{user.full_name}</h2>
            <p className="subtle-copy">
              {user.role} | {user.username} | {user.auth_provider}
            </p>
          </div>
        </div>

        <div className="profile-glance-grid">
          <article className="status-card elevated-card">
            <span>Email</span>
            <strong>{user.email || "Not set"}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Organization</span>
            <strong>{user.preferences?.organization || "Independent"}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Department</span>
            <strong>{user.preferences?.department || "General access"}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Last login</span>
            <strong>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "First session"}</strong>
          </article>
        </div>
      </section>

      <section className="panel panel-span-8">
        <div className="panel-header">
          <h3>Profile details</h3>
          <span className="subtle-copy">Editable identity and working preferences</span>
        </div>

        <form className="profile-form" onSubmit={submit}>
          <div className="form-grid">
            <label className="field">
              <span>Full name</span>
              <input name="full_name" value={form.full_name} onChange={updateField} />
            </label>

            <label className="field">
              <span>Email</span>
              <input name="email" value={form.email} onChange={updateField} />
            </label>

            <label className="field">
              <span>Title</span>
              <input name="title" value={form.title} onChange={updateField} />
            </label>

            <label className="field">
              <span>Department</span>
              <input name="department" value={form.department} onChange={updateField} />
            </label>

            <label className="field">
              <span>Organization</span>
              <input name="organization" value={form.organization} onChange={updateField} />
            </label>

            <label className="field">
              <span>Phone</span>
              <input name="phone" value={form.phone} onChange={updateField} />
            </label>

            <label className="field">
              <span>Location</span>
              <input name="location" value={form.location} onChange={updateField} />
            </label>

            <label className="field">
              <span>Default workspace</span>
              <select name="dashboard_view" value={form.dashboard_view} onChange={updateField}>
                <option value="operations">Operations</option>
                <option value="patient-command">Patient command</option>
                <option value="analytics">Analytics</option>
                <option value="reports">Reports</option>
              </select>
            </label>

            <label className="field">
              <span>Notification mode</span>
              <select
                name="notification_preference"
                value={form.notification_preference}
                onChange={updateField}
              >
                <option value="critical">Critical only</option>
                <option value="operations">Operational</option>
                <option value="all">All updates</option>
              </select>
            </label>
          </div>

          <label className="field">
            <span>Professional bio</span>
            <textarea name="bio" value={form.bio} onChange={updateField} rows={4} />
          </label>

          {user.auth_provider === "local" ? (
            <div className="form-grid">
              <label className="field">
                <span>Current password</span>
                <input
                  type="password"
                  name="current_password"
                  value={form.current_password}
                  onChange={updateField}
                  autoComplete="current-password"
                />
              </label>

              <label className="field">
                <span>New password</span>
                <input
                  type="password"
                  name="new_password"
                  value={form.new_password}
                  onChange={updateField}
                  autoComplete="new-password"
                />
              </label>
            </div>
          ) : (
            <p className="subtle-copy">Password changes are handled by your identity provider for this account.</p>
          )}

          <div className="form-actions">
            <button className="primary-button accent-button" type="submit" disabled={busy}>
              {busy ? "Saving..." : "Save profile"}
            </button>
            {message ? <span className="success-text">{message}</span> : null}
          </div>

          {error ? <p className="error-text">{error}</p> : null}
        </form>
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Account context</h3>
          <span className="subtle-copy">Current access level</span>
        </div>

        <div className="queue-list">
          <article className="status-card elevated-card">
            <span>Role</span>
            <strong>{user.role}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Provider</span>
            <strong>{user.auth_provider}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Organization</span>
            <strong>{user.organization_name || "HealthSphere Medical"}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Preferred workspace</span>
            <strong>{user.preferences?.dashboard_view || "operations"}</strong>
          </article>
          <article className="status-card elevated-card">
            <span>Notification mode</span>
            <strong>{user.preferences?.notification_preference || "critical"}</strong>
          </article>
        </div>
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Active sessions</h3>
          <div className="report-actions-row">
            <span className="subtle-copy">{sessions.length} active records</span>
            <button className="secondary-button small-button" type="button" onClick={() => void revokeAllSessions()} disabled={sessionActionBusy}>
              Revoke all
            </button>
          </div>
        </div>

        {sessionsError ? <p className="error-text">{getRequestErrorMessage(sessionsError, "Unable to load session history.")}</p> : null}
        {sessionError ? <p className="error-text">{sessionError}</p> : null}

        <div className="queue-list compact-list">
          {sessions.map((session) => (
            <article key={session.session_id} className="queue-row">
              <div>
                <strong>{session.current ? "Current session" : "Signed-in session"}</strong>
                <p className="subtle-copy">
                  Last used {new Date(session.last_used_at).toLocaleString()} | expires {new Date(session.expires_at).toLocaleString()}
                </p>
                <p className="subtle-copy">{session.user_agent || "Unknown device"}</p>
              </div>
              {!session.current ? (
                <button
                  className="secondary-button small-button"
                  type="button"
                  onClick={() => void revokeSingleSession(session.session_id)}
                  disabled={sessionActionBusy}
                >
                  Revoke
                </button>
              ) : (
                <span className="tone tone-low">current</span>
              )}
            </article>
          ))}
          {sessions.length === 0 ? <p className="subtle-copy">No session records are available yet.</p> : null}
        </div>
      </section>
    </div>
  );
};

export default Profile;
