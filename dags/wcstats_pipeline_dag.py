from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup


PROJECT_DIR = "/opt/airflow/project"
PYTHON_BIN = "python"

default_args = {
    "owner": "caio",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def pipeline_task(task_id, script_path):
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"PYTHONPATH={PROJECT_DIR}/src {PYTHON_BIN} {script_path}"
        ),
    )


with DAG(
    dag_id="wcstats_reference_pipeline",
    default_args=default_args,
    description="Carga manual de dados de referencia do WCStats",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["wcstats", "reference", "manual"],
) as reference_dag:

    with TaskGroup("extract_reference") as extract_reference:
        extract_worldcup_teams = pipeline_task(
            "extract_worldcup_teams",
            "src/01_extract/extract_worldcup_teams.py",
        )
        extract_matches_reference = pipeline_task(
            "extract_matches_reference",
            "src/01_extract/extract_matches.py",
        )
        extract_historical_matches = pipeline_task(
            "extract_historical_matches",
            "src/01_extract/extract_historical_matches.py",
        )
        extract_fifa_ranking = pipeline_task(
            "extract_fifa_ranking",
            "src/01_extract/extract_fifa_ranking.py",
        )
        extract_hdi_data = pipeline_task(
            "extract_hdi_data",
            "src/01_extract/extract_hdi_data.py",
        )
        extract_team_market_value = pipeline_task(
            "extract_team_market_value",
            "src/01_extract/extract_team_market_value.py",
        )
        extract_worldbank_data = pipeline_task(
            "extract_worldbank_data",
            "src/01_extract/extract_worldbank_data.py",
        )
        extract_country_top_cities = pipeline_task(
            "extract_country_top_cities",
            "src/01_extract/extract_country_top_cities.py",
        )
        extract_country_city_environment = pipeline_task(
            "extract_country_city_environment",
            "src/01_extract/extract_country_city_environment.py",
        )

        extract_country_top_cities >> extract_country_city_environment

    with TaskGroup("build_reference_marts") as build_reference_marts:
        transform_dim_country = pipeline_task(
            "transform_dim_country",
            "src/02_transform/transform_dim_country.py",
        )
        transform_team_mapping = pipeline_task(
            "transform_team_mapping",
            "src/02_transform/transform_team_mapping.py",
        )
        transform_team_ranking = pipeline_task(
            "transform_team_ranking",
            "src/02_transform/transform_team_ranking.py",
        )
        create_country_latest_indicators = pipeline_task(
            "create_country_latest_indicators",
            "src/03_mart/create_country_latest_indicators.py",
        )
        create_country_latest_hdi = pipeline_task(
            "create_country_latest_hdi",
            "src/03_mart/create_country_latest_hdi.py",
        )
        create_team_country_indicators = pipeline_task(
            "create_team_country_indicators",
            "src/03_mart/create_team_country_indicators.py",
        )
        create_team_hdi = pipeline_task(
            "create_team_hdi",
            "src/03_mart/create_team_hdi.py",
        )
        create_team_environment_profile = pipeline_task(
            "create_team_environment_profile",
            "src/03_mart/create_team_environment_profile.py",
        )
        create_team_market_value = pipeline_task(
            "create_team_market_value",
            "src/03_mart/create_team_market_value.py",
        )

        create_country_latest_indicators >> create_team_country_indicators
        create_country_latest_hdi >> create_team_hdi

    extract_worldcup_teams >> transform_dim_country
    [extract_matches_reference, extract_historical_matches] >> transform_team_mapping
    transform_dim_country >> [
        extract_worldbank_data,
        extract_country_top_cities,
    ]

    [transform_dim_country, extract_fifa_ranking] >> transform_team_ranking
    [transform_dim_country, extract_worldbank_data] >> create_country_latest_indicators
    [transform_dim_country, extract_hdi_data] >> create_country_latest_hdi
    [transform_dim_country, extract_team_market_value] >> create_team_market_value
    [transform_dim_country, extract_country_city_environment] >> create_team_environment_profile


with DAG(
    dag_id="wcstats_pipeline",
    default_args=default_args,
    description="Pipeline diaria enxuta do projeto WCStats",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["wcstats", "worldcup", "etl"],
) as dag:

    with TaskGroup("extract_daily") as extract_daily:
        check_reference_tables = pipeline_task(
            "check_reference_tables",
            "src/check_reference_tables.py",
        )
        extract_matches = pipeline_task(
            "extract_matches",
            "src/01_extract/extract_matches.py",
        )

        check_reference_tables >> extract_matches

    with TaskGroup("transform_daily") as transform_daily:
        transform_team_mapping = pipeline_task(
            "transform_team_mapping",
            "src/02_transform/transform_team_mapping.py",
        )
        transform_matches_clean = pipeline_task(
            "transform_matches_clean",
            "src/02_transform/transform_matches_clean.py",
        )

        transform_team_mapping >> transform_matches_clean

    with TaskGroup("mart_daily") as mart_daily:
        create_team_recent_strength = pipeline_task(
            "create_team_recent_strength",
            "src/03_mart/create_team_recent_strength.py",
        )
        create_team_historical_strength = pipeline_task(
            "create_team_historical_strength",
            "src/03_mart/create_team_historical_strength.py",
        )
        create_team_elo = pipeline_task(
            "create_team_elo",
            "src/03_mart/create_team_elo.py",
        )
        create_team_strength_score = pipeline_task(
            "create_team_strength_score",
            "src/03_mart/create_team_strength_score.py",
        )
        create_team_goal_profile = pipeline_task(
            "create_team_goal_profile",
            "src/03_mart/create_team_goal_profile.py",
        )
        create_worldcup_fixtures = pipeline_task(
            "create_worldcup_fixtures",
            "src/03_mart/create_worldcup_fixtures.py",
        )
        create_future_match_predictions = pipeline_task(
            "create_future_match_predictions",
            "src/03_mart/create_future_match_predictions.py",
        )
        create_score_probabilities = pipeline_task(
            "create_score_probabilities",
            "src/03_mart/create_score_probabilities.py",
        )
        create_group_standings = pipeline_task(
            "create_group_standings",
            "src/03_mart/create_group_standings.py",
        )
        transform_match_features = pipeline_task(
            "transform_match_features",
            "src/02_transform/transform_match_features.py",
        )
        create_match_predictions = pipeline_task(
            "create_match_predictions",
            "src/03_mart/create_match_predictions.py",
        )
        create_match_xg = pipeline_task(
            "create_match_xg",
            "src/03_mart/create_match_xg.py",
        )

        [
            create_team_recent_strength,
            create_team_historical_strength,
            create_team_elo,
        ] >> create_team_strength_score

        create_team_strength_score >> [
            create_team_goal_profile,
            create_worldcup_fixtures,
            transform_match_features,
        ]

        [create_team_goal_profile, create_worldcup_fixtures] >> create_future_match_predictions
        create_future_match_predictions >> create_score_probabilities
        create_worldcup_fixtures >> create_group_standings
        transform_match_features >> [create_match_predictions, create_match_xg]

    with TaskGroup("views") as views:
        create_match_center_views = pipeline_task(
            "create_match_center_views",
            "src/04_views/create_match_center_views.py",
        )

    extract_matches >> transform_team_mapping
    [extract_matches, transform_team_mapping] >> transform_matches_clean

    transform_matches_clean >> [
        create_team_recent_strength,
        create_team_historical_strength,
        create_team_elo,
    ]

    [
        create_score_probabilities,
        create_group_standings,
        create_match_predictions,
        create_match_xg,
    ] >> create_match_center_views
