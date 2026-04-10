import React, { useMemo, useState } from "react";
import useSWR from "swr";

import NotificationsPanel from "../components/NotificationsPanel";
import { getRequestErrorMessage, markNotificationRead } from "../services/api";

const toneClassName = (tone) => `tone tone-${tone || "low"}`;

const Notifications = () => {
  const [filterMode, setFilterMode] = useState("all");
  const [busyIds, setBusyIds] = useState([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  const {
    data: notifications = [],
    error,
    isLoading,
    mutate,
  } = useSWR(["notifications", 40, false]);

  const filteredNotifications = useMemo(() => {
    if (filterMode === "unread") {
      return notifications.filter((notification) => !notification.is_read);
    }
    if (filterMode === "read") {
      return notifications.filter((notification) => notification.is_read);
    }
    return notifications;
  }, [filterMode, notifications]);

  const notificationMetrics = useMemo(() => {
    const unread = notifications.filter((notification) => !notification.is_read).length;
    const critical = notifications.filter((notification) => notification.severity === "critical" && !notification.is_read).length;
    const operations = notifications.filter((notification) => notification.category === "operations" && !notification.is_read).length;

    return [
      { label: "Inbox items", value: notifications.length, tone: "low" },
      { label: "Unread", value: unread, tone: unread > 0 ? "medium" : "low" },
      { label: "Critical unread", value: critical, tone: critical > 0 ? "critical" : "low" },
      { label: "Operations", value: operations, tone: operations > 0 ? "high" : "low" },
    ];
  }, [notifications]);

  const visibleUnreadIds = useMemo(
    () => filteredNotifications.filter((notification) => !notification.is_read).map((notification) => notification.notification_id),
    [filteredNotifications]
  );

  const updateBusyState = (notificationId, isBusy) => {
    setBusyIds((current) => {
      if (isBusy) {
        return current.includes(notificationId) ? current : [...current, notificationId];
      }
      return current.filter((item) => item !== notificationId);
    });
  };

  const markRead = async (notificationId) => {
    try {
      setActionError("");
      updateBusyState(notificationId, true);
      const updated = await markNotificationRead(notificationId);
      mutate(
        (current = []) =>
          current.map((notification) =>
            notification.notification_id === updated.notification_id ? updated : notification
          ),
        false
      );
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to update notification status."));
    } finally {
      updateBusyState(notificationId, false);
    }
  };

  const markVisibleRead = async () => {
    if (!visibleUnreadIds.length) {
      return;
    }

    try {
      setBulkBusy(true);
      setActionError("");
      const updates = await Promise.all(visibleUnreadIds.map((notificationId) => markNotificationRead(notificationId)));
      const updateMap = new Map(updates.map((notification) => [notification.notification_id, notification]));
      mutate(
        (current = []) => current.map((notification) => updateMap.get(notification.notification_id) || notification),
        false
      );
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to clear visible notifications."));
    } finally {
      setBulkBusy(false);
    }
  };

  if (isLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading notification workspace...</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load notifications</strong>
          <p>{getRequestErrorMessage(error, "Please try again.")}</p>
          <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Operator inbox</p>
          <h2>Notification workspace</h2>
          <p className="subtle-copy">Unread alerts, workflow completions, and operational follow-through.</p>
        </div>

        <div className="hero-badges">
          <span className={toneClassName(notificationMetrics[1].value > 0 ? "medium" : "low")}>
            {notificationMetrics[1].value} unread
          </span>
          <span className={toneClassName(notificationMetrics[2].value > 0 ? "critical" : "low")}>
            {notificationMetrics[2].value} critical unread
          </span>
        </div>
      </section>

      <section className="metrics-grid workspace-kpi-grid">
        {notificationMetrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      {actionError ? (
        <section className="feedback-banner is-error">
          <p>{actionError}</p>
        </section>
      ) : null}

      <section className="panel full-span">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Inbox controls</h3>
            <p>Filter the visible queue and clear handled items quickly.</p>
          </div>
          <span className="subtle-copy">{filteredNotifications.length} visible</span>
        </div>

        <div className="notification-toolbar">
          <div className="filter-row directory-filter-row">
            <button
              className={`filter-chip ${filterMode === "all" ? "active" : ""}`}
              type="button"
              onClick={() => setFilterMode("all")}
            >
              All
              <span className="filter-chip-count">{notifications.length}</span>
            </button>
            <button
              className={`filter-chip ${filterMode === "unread" ? "active" : ""}`}
              type="button"
              onClick={() => setFilterMode("unread")}
            >
              Unread
              <span className="filter-chip-count">{notificationMetrics[1].value}</span>
            </button>
            <button
              className={`filter-chip ${filterMode === "read" ? "active" : ""}`}
              type="button"
              onClick={() => setFilterMode("read")}
            >
              Read
              <span className="filter-chip-count">{notifications.length - notificationMetrics[1].value}</span>
            </button>
          </div>

          <div className="toolbar-actions">
            <span className="toolbar-note">
              {visibleUnreadIds.length} unread in the current view
            </span>
            <button
              className="secondary-button small-button"
              type="button"
              disabled={bulkBusy || visibleUnreadIds.length === 0}
              onClick={() => void markVisibleRead()}
            >
              {bulkBusy ? "Updating..." : "Mark visible read"}
            </button>
          </div>
        </div>
      </section>

      <NotificationsPanel
        notifications={filteredNotifications}
        onMarkRead={markRead}
        busyIds={busyIds}
        className="full-span"
        title="Notification inbox"
        description="Review the current queue and clear items once the follow-up is complete."
      />
    </div>
  );
};

export default Notifications;
