from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from backend.app.core.config import get_settings
from backend.app.db.repository import list_alerts, prune_notifications
from backend.app.db.session import SessionLocal


def reconcile_alert_queue() -> dict[str, int]:
    with SessionLocal() as db:
        open_alerts = [alert for alert in list_alerts(db) if not alert.acknowledged]
    return {
        "open_alerts": len(open_alerts),
        "critical_alerts": sum(1 for alert in open_alerts if alert.severity == "critical"),
    }


def prune_notification_backlog() -> int:
    settings = get_settings()
    with SessionLocal() as db:
        return prune_notifications(db, settings.notification_retention_days)


with DAG(
    dag_id="healthsphere_alert_review",
    start_date=datetime(2024, 1, 1),
    schedule="*/30 * * * *",
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["operations", "alerts"],
) as dag:
    reconcile = PythonOperator(
        task_id="reconcile_alert_queue",
        python_callable=reconcile_alert_queue,
    )

    prune = PythonOperator(
        task_id="prune_notification_backlog",
        python_callable=prune_notification_backlog,
    )

    reconcile >> prune
