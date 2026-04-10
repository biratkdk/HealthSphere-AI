import React from "react";

const NotificationsPanel = ({
  notifications,
  onMarkRead,
  busyIds = [],
  className = "",
  title = "Notification inbox",
  description = "Review unread activity and clear items as they are handled.",
}) => {
  const busySet = new Set(busyIds);

  return (
    <section className={`panel ${className}`.trim()}>
      <div className="panel-header">
        <div className="panel-header-stack">
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <span className="subtle-copy">{notifications.length} items</span>
      </div>

      <div className="notification-list">
        {notifications.map((notification) => {
          const busy = busySet.has(notification.notification_id);
          return (
            <article
              key={notification.notification_id}
              className={`notification-item elevated-card severity-${notification.severity} ${notification.is_read ? "is-read" : ""}`}
            >
              <div className="notification-top">
                <div className="panel-header-stack">
                  <strong>{notification.title}</strong>
                  <p>{new Date(notification.created_at).toLocaleString()}</p>
                </div>

                <div className="notification-status-row">
                  <span className={`tone tone-${notification.severity}`}>{notification.severity}</span>
                  <span className="notification-category-tag">{notification.category}</span>
                  {!notification.is_read ? (
                    <button
                      className="secondary-button small-button"
                      type="button"
                      onClick={() => onMarkRead(notification.notification_id)}
                      disabled={busy}
                    >
                      {busy ? "Marking..." : "Mark read"}
                    </button>
                  ) : (
                    <span className="tone tone-low">Read</span>
                  )}
                </div>
              </div>

              <p className="notification-body">{notification.body}</p>
            </article>
          );
        })}

        {notifications.length === 0 ? <p className="subtle-copy">No notifications are waiting in this view.</p> : null}
      </div>
    </section>
  );
};

export default NotificationsPanel;
