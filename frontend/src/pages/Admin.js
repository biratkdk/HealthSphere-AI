import React, { useState } from "react";
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
    mutate: mutateUsers,
  } = useSWR(user?.role === "admin" ? ["adminUsers", 150] : null);
  const {
    data: invites = [],
    error: invitesError,
    mutate: mutateInvites,
  } = useSWR(user?.role === "admin" ? ["inviteCodes", 50] : null);

  if (user?.role !== "admin") {
    return <section className="panel error-panel">Admin access is required for this view.</section>;
  }

  if (isLoading) {
    return <section className="panel">Loading audit activity...</section>;
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
      mutateUsers((current = []) => current, false);
      setInviteForm({ role: "clinician", email: "", expires_in_days: 7 });
      setMessage(`Invite created: ${created.invite_code}`);
    } catch (requestError) {
      setMessage(getRequestErrorMessage(requestError, "Unable to create the invite."));
    }
  };

  const replaceUserInDirectory = (updatedUser) => {
    mutateUsers((current = []) =>
      current.map((member) => (member.username === updatedUser.username ? updatedUser : member)),
    false);
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
          <h2>Audit activity</h2>
          <p className="subtle-copy">Review workspace access, issue invites, and inspect authenticated activity.</p>
        </div>
      </section>

      <section className="panel panel-span-5">
        <div className="panel-header">
          <h3>Organization users</h3>
          <span className="subtle-copy">{users.length} active accounts</span>
        </div>

        {usersError ? <p className="error-text">{getRequestErrorMessage(usersError, "Unable to load users.")}</p> : null}
        {memberMessage ? <p className={memberMessage.includes("Unable") ? "error-text" : "success-text"}>{memberMessage}</p> : null}

        <div className="queue-list compact-list">
          {users.map((member) => (
            <article key={member.username} className="queue-row">
              <div>
                <strong>{member.full_name}</strong>
                <p className="subtle-copy">
                  {member.role} | {member.auth_provider}
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
                <span className={`tone ${member.is_active ? "tone-low" : "tone-high"}`}>{member.is_active ? "active" : "inactive"}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel panel-span-7">
        <div className="panel-header">
          <h3>Access invites</h3>
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
                placeholder="Optional email allowlist"
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

        {message ? <p className={message.startsWith("Invite created:") ? "success-text" : "error-text"}>{message}</p> : null}
        {invitesError ? <p className="error-text">{getRequestErrorMessage(invitesError, "Unable to load invites.")}</p> : null}

        <div className="queue-list compact-list">
          {invites.map((invite) => (
            <article key={invite.invite_id} className="queue-row">
              <div>
                <strong>{invite.role}</strong>
                <p className="subtle-copy">
                  {invite.email || "open invite"} | expires {new Date(invite.expires_at).toLocaleDateString()}
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
          <h3>Recent events</h3>
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
