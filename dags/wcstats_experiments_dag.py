from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/project"
PYTHON_BIN = "python"

default_args = {
    "owner": "caio",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def experiment_task(task_id, script_path):
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"PYTHONPATH={PROJECT_DIR}/src:{PROJECT_DIR}/src/05_experiments "
            f"{PYTHON_BIN} {script_path}"
        ),
    )


with DAG(
    dag_id="wcstats_experiments_pipeline",
    default_args=default_args,
    description="Pipeline manual para backtests e estudos de modelos preditivos do WCStats",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["wcstats", "experiments", "models", "manual"],
) as dag:

    check_experiment_dependencies = experiment_task(
        "check_experiment_dependencies",
        "src/05_experiments/check_experiment_dependencies.py",
    )

    create_prediction_model_lab = experiment_task(
        "create_prediction_model_lab",
        "src/05_experiments/create_prediction_model_lab.py",
    )

    check_experiment_dependencies >> create_prediction_model_lab
