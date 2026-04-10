import React from "react";

const NotificationsPanel = ({ notifications, onMarkRead, className = "" }) => {
  return (
    <section className={`panel ${className}`.trim()}>
      <div className="panel-header">
        <h3>Notification inbox</h3>
        <span className="subtle-copy">{notifications.length} recent items</span>
      </div>

      <div className="notification-list">
        {notifications.map((notification) => (
          <article
            key={notification.notification_id}
            className={`notification-item elevated-card severity-${notification.severity} ${notification.is_read ? "is-read" : ""}`}
          >
            <div className="notification-top">
              <div>
                <strong>{notification.title}</strong>
                <p className="subtle-copy">
                  {notification.category} | {new Date(notification.created_at).toLocaleString()}
                </p>
              </div>
              {!notification.is_read ? (
                <button
                  className="secondary-button small-button"
                  type="button"
                  onClick={() => onMarkRead(notification.notification_id)}
                >
                  Mark read
                </button>
              ) : (
                <span className="tone tone-low">read</span>
              )}
            </div>
            <p>{notification.body}</p>
          </article>
        ))}

        {notifications.length === 0 ? <p className="subtle-copy">No notifications are waiting for this user.</p> : null}
      </div>
    </section>
  );
};

export default NotificationsPanel;
