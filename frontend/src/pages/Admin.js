import React, { useMemo, useState } from "react";
import useSWR from "swr";

import { useAuth } from "../context/AuthContext";
import { createInviteCode, getRequestErrorMessage, updateAdminUserRole, updateAdminUserStatus } from "../services/api";

const Admin = () => {
  const { user } = useAuth();
  const [inviteForm, setInviteForm] = useState({ role: "clinician", email: "", expires_in_days: 7 });
  const [message, setMessage] = useState("");
  const [memberMessage, setMemberMessage] = useState("");
  const [memberActionBusy, setMemberActionBusy] = useState("");
  const [roleDrafts, setRoleDrafts] = useState({});

  const {
    data: logs = [],
    error,
    isLoading,
  } = useSWR(user?.role === "admin" ? ["auditLogs", 75] : null);

  const {
    data: users = [],
    error: usersError,
    isLoading: usersLoading,
    mutate: mutateUsers,
  } = useSWR(user?.role === "admin" ? ["adminUsers", 150] : null);

  const {
    data: invites = [],
    error: invitesError,
    isLoading: invitesLoading,
    mutate: mutateInvites,
  } = useSWR(user?.role === "admin" ? ["inviteCodes", 50] : null);

  const adminMetrics = useMemo(() => {
    const activeUsers = users.filter((member) => member.is_active).length;
    const inactiveUsers = users.length - activeUsers;
    const adminUsers = users.filter((member) => member.role === "admin").length;
    const pendingInvites = invites.filter((invite) => invite.status === "pending").length;

    return [
      { label: "Users", value: users.length, tone: "low" },
      { label: "Active", value: activeUsers, tone: "low" },
      { label: "Inactive", value: inactiveUsers, tone: inactiveUsers > 0 ? "high" : "low" },
      { label: "Admins", value: adminUsers, tone: adminUsers > 0 ? "medium" : "low" },
      { label: "Pending invites", value: pendingInvites, tone: pendingInvites > 0 ? "medium" : "low" },
      { label: "Audit events", value: logs.length, tone: "low" },
    ];
  }, [invites, logs.length, users]);

  if (user?.role !== "admin") {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Admin access is required for this view.</strong>
        </section>
      </div>
    );
  }

  if (isLoading || usersLoading || invitesLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading admin workspace...</p>
        </section>
      </div>
    );
  }

  const submitInvite = async (event) => {
    event.preventDefault();
    setMessage("");
    setMemberMessage("");

    try {
      const payload = {
        role: inviteForm.role,
        expires_in_days: Number(inviteForm.expires_in_days),
      };

      if (inviteForm.email.trim()) {
        payload.email = inviteForm.email.trim();
      }

      const created = await createInviteCode(payload);
      mutateInvites((current = []) => [created, ...current], false);
      setInviteForm({ role: "clinician", email: "", expires_in_days: 7 });
      setMessage(`Invite created: ${created.invite_code}`);
    } catch (requestError) {
      setMessage(getRequestErrorMessage(requestError, "Unable to create the invite."));
    }
  };

  const replaceUserInDirectory = (updatedUser) => {
    mutateUsers(
      (current = []) => current.map((member) => (member.username === updatedUser.username ? updatedUser : member)),
      false
    );
  };

  const submitRoleUpdate = async (member) => {
    const nextRole = roleDrafts[member.username] || member.role;
    if (nextRole === member.role) {
      return;
    }

    try {
      setMemberActionBusy(member.username);
      setMemberMessage("");
      const updated = await updateAdminUserRole(member.username, nextRole);
      replaceUserInDirectory(updated);
      setRoleDrafts((current) => ({ ...current, [member.username]: updated.role }));
      setMemberMessage(`Updated ${updated.full_name} to ${updated.role}.`);
    } catch (requestError) {
      setMemberMessage(getRequestErrorMessage(requestError, "Unable to update the user role."));
    } finally {
      setMemberActionBusy("");
    }
  };

  const toggleUserStatus = async (member) => {
    try {
      setMemberActionBusy(member.username);
      setMemberMessage("");
      const updated = await updateAdminUserStatus(member.username, !member.is_active);
      replaceUserInDirectory(updated);
      setMemberMessage(`${updated.full_name} is now ${updated.is_active ? "active" : "inactive"}.`);
    } catch (requestError) {
      setMemberMessage(getRequestErrorMessage(requestError, "Unable to update account access."));
    } finally {
      setMemberActionBusy("");
    }
  };

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Governance console</p>
          <h2>Admin workspace</h2>
          <p className="subtle-copy">Access control, invite issuance, and audit activity for the current organization.</p>
        </div>

        <div className="hero-badges">
          <span className="tone tone-low">{users.length} users</span>
          <span className="tone tone-medium">{invites.filter((invite) => invite.status === "pending").length} pending invites</span>
          <span className="tone tone-low">{logs.length} audit events</span>
        </div>
      </section>

      <section className="metrics-grid workspace-kpi-grid">
        {adminMetrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      {memberMessage ? (
        <section className={`feedback-banner ${memberMessage.includes("Unable") ? "is-error" : "is-success"}`}>
          <p>{memberMessage}</p>
        </section>
      ) : null}

      {message ? (
        <section className={`feedback-banner ${message.startsWith("Invite created:") ? "is-success" : "is-error"}`}>
          <p>{message}</p>
        </section>
      ) : null}

      <section className="panel panel-span-5">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Organization users</h3>
            <p>Adjust roles and workspace access for current members.</p>
          </div>
          <span className="subtle-copy">{users.length} accounts</span>
        </div>

        {usersError ? <p className="error-text">{getRequestErrorMessage(usersError, "Unable to load users.")}</p> : null}

        <div className="queue-list compact-list">
          {users.map((member) => (
            <article key={member.username} className="queue-row">
              <div className="directory-card-copy">
                <strong>{member.full_name}</strong>
                <p className="subtle-copy">
                  {member.role} &middot; {member.auth_provider}
                </p>
                <p className="subtle-copy">{member.email || member.username}</p>
              </div>

              <div className="directory-actions">
                <label className="field compact-field">
                  <span>Role</span>
                  <select
                    value={roleDrafts[member.username] || member.role}
                    onChange={(event) =>
                      setRoleDrafts((current) => ({ ...current, [member.username]: event.target.value }))
                    }
                    disabled={memberActionBusy === member.username}
                  >
                    <option value="admin">Admin</option>
                    <option value="clinician">Clinician</option>
                    <option value="analyst">Analyst</option>
                  </select>
                </label>

                <button
                  className="secondary-button small-button"
                  type="button"
                  onClick={() => void submitRoleUpdate(member)}
                  disabled={memberActionBusy === member.username || (roleDrafts[member.username] || member.role) === member.role}
                >
                  Save role
                </button>

                <button
                  className="secondary-button small-button"
                  type="button"
                  onClick={() => void toggleUserStatus(member)}
                  disabled={memberActionBusy === member.username}
                >
                  {member.is_active ? "Deactivate" : "Reactivate"}
                </button>

                <span className={`tone ${member.is_active ? "tone-low" : "tone-high"}`}>
                  {member.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel panel-span-7">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Access invites</h3>
            <p>Create scoped invite codes and review recent usage.</p>
          </div>
          <span className="subtle-copy">{invites.length} recent invites</span>
        </div>

        <form className="task-form" onSubmit={submitInvite}>
          <div className="form-grid">
            <label className="field">
              <span>Role</span>
              <select
                value={inviteForm.role}
                onChange={(event) => setInviteForm((current) => ({ ...current, role: event.target.value }))}
              >
                <option value="clinician">Clinician</option>
                <option value="analyst">Analyst</option>
              </select>
            </label>

            <label className="field">
              <span>Email restriction</span>
              <input
                value={inviteForm.email}
                onChange={(event) => setInviteForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="Optional email restriction"
              />
            </label>

            <label className="field">
              <span>Expiry (days)</span>
              <input
                type="number"
                min="1"
                max="30"
                value={inviteForm.expires_in_days}
                onChange={(event) => setInviteForm((current) => ({ ...current, expires_in_days: event.target.value }))}
              />
            </label>
          </div>

          <button className="primary-button accent-button" type="submit">
            Create invite
          </button>
        </form>

        {invitesError ? <p className="error-text">{getRequestErrorMessage(invitesError, "Unable to load invites.")}</p> : null}

        <div className="queue-list compact-list">
          {invites.map((invite) => (
            <article key={invite.invite_id} className="queue-row">
              <div className="directory-card-copy">
                <strong>{invite.role}</strong>
                <p className="subtle-copy">
                  {invite.email || "Open invite"} &middot; expires {new Date(invite.expires_at).toLocaleDateString()}
                </p>
                <p className="subtle-copy">{invite.invite_code || invite.invite_id}</p>
              </div>
              <span className={`tone tone-${invite.status === "pending" ? "medium" : invite.status === "accepted" ? "low" : "high"}`}>
                {invite.status}
              </span>
            </article>
          ))}
        </div>
      </section>

      <section className="panel audit-panel">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Recent events</h3>
            <p>Authenticated activity and request outcomes across the workspace.</p>
          </div>
          <span className="subtle-copy">{logs.length} records</span>
        </div>

        {error ? <p className="error-text">{getRequestErrorMessage(error, "Unable to load audit activity.")}</p> : null}

        <div className="audit-list">
          {logs.map((log) => (
            <article key={log.audit_id} className="audit-row">
              <div className="audit-row-top">
                <strong>{log.method}</strong>
                <span>{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <p>{log.path}</p>
              <div className="audit-meta">
                <span>User: {log.actor_username}</span>
                <span>Role: {log.actor_role}</span>
                <span>Status: {log.status_code}</span>
              </div>
              {log.detail ? <pre className="detail-block">{JSON.stringify(log.detail, null, 2)}</pre> : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Admin;
