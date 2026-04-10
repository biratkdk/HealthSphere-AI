import React from "react";
import useSWR from "swr";

import NotificationsPanel from "../components/NotificationsPanel";
import { getRequestErrorMessage, markNotificationRead } from "../services/api";

const Notifications = () => {
  const {
    data: notifications = [],
    error,
    isLoading,
    mutate,
  } = useSWR(["notifications", 40, false]);

  const markRead = async (notificationId) => {
    const updated = await markNotificationRead(notificationId);
    mutate(
      (current = []) =>
        current.map((notification) =>
          notification.notification_id === updated.notification_id ? updated : notification
        ),
      false
    );
  };

  if (isLoading) {
    return <section className="panel">Loading notification inbox...</section>;
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Operator inbox</p>
          <h2>Notifications</h2>
          <p className="subtle-copy">Review imaging completions, report availability, and operational events.</p>
        </div>
      </section>

      {error ? <section className="panel error-panel">{getRequestErrorMessage(error, "Unable to load notifications.")}</section> : null}
      <NotificationsPanel notifications={notifications} onMarkRead={markRead} className="full-span" />
    </div>
  );
};

export default Notifications;
