from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from backend.app.workers.retraining import (
    plan_retraining_window,
    publish_retraining_manifest,
    run_training_job,
)


with DAG(
    dag_id="healthsphere_retraining",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * 0",
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=15)},
    tags=["ml", "retraining"],
) as dag:
    plan = PythonOperator(
        task_id="plan_retraining_window",
        python_callable=plan_retraining_window,
    )

    train_icu = PythonOperator(
        task_id="train_icu_model",
        python_callable=run_training_job,
        op_kwargs={"model_name": "icu_deterioration_lstm"},
    )

    train_disease = PythonOperator(
        task_id="train_disease_model",
        python_callable=run_training_job,
        op_kwargs={"model_name": "disease_risk_xgboost"},
    )

    train_imaging = PythonOperator(
        task_id="train_imaging_model",
        python_callable=run_training_job,
        op_kwargs={"model_name": "imaging_triage_cnn"},
    )

    train_treatment = PythonOperator(
        task_id="train_treatment_policy",
        python_callable=run_training_job,
        op_kwargs={"model_name": "care_plan_recommendation_policy"},
    )

    publish = PythonOperator(
        task_id="publish_retraining_manifest",
        python_callable=publish_retraining_manifest,
    )

    plan >> [train_icu, train_disease, train_imaging, train_treatment] >> publish
