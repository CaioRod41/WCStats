import math

import numpy as np
import pandas as pd
from sqlalchemy import inspect, text

from config import create_engine, database_url, overwrite_table


engine = create_engine(database_url())

COMPONENTS = [
    "recent_score",
    "market_score",
    "historical_score",
    "fifa_score",
    "elo_score",
    "environment_score",
    "socioeconomic_score",
]

MODEL_CANDIDATES = [
    {
        "model_id": "baseline_current",
        "model_name": "Baseline atual",
        "model_family": "weighted_strength",
        "description": "Pesos atuais usados no team_strength_score oficial.",
        "weights": {
            "recent_score": 0.40,
            "market_score": 0.23,
            "historical_score": 0.10,
            "fifa_score": 0.10,
            "elo_score": 0.10,
            "environment_score": 0.02,
            "socioeconomic_score": 0.05,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
    {
        "model_id": "baseline_without_socio",
        "model_name": "Baseline sem socioeconomico",
        "model_family": "ablation_study",
        "description": "Mantem o baseline, remove socioeconomico e redistribui o peso nos demais sinais.",
        "weights": {
            "recent_score": 0.37,
            "market_score": 0.28,
            "historical_score": 0.13,
            "fifa_score": 0.08,
            "elo_score": 0.07,
            "environment_score": 0.04,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
    {
        "model_id": "baseline_without_environment",
        "model_name": "Baseline sem environment",
        "model_family": "ablation_study",
        "description": "Mantem o baseline, remove environment e redistribui o peso nos demais sinais.",
        "weights": {
            "recent_score": 0.37,
            "market_score": 0.28,
            "historical_score": 0.13,
            "fifa_score": 0.08,
            "elo_score": 0.07,
            "environment_score": 0.00,
            "socioeconomic_score": 0.03,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
    {
        "model_id": "baseline_core_only",
        "model_name": "Baseline sem socio/environment",
        "model_family": "ablation_study",
        "description": "Mantem somente performance, mercado, FIFA e Elo; remove socioeconomico e environment.",
        "weights": {
            "recent_score": 0.37,
            "market_score": 0.28,
            "historical_score": 0.13,
            "fifa_score": 0.08,
            "elo_score": 0.07,
            "environment_score": 0.00,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
    {
        "model_id": "balanced_components",
        "model_name": "Componentes balanceados",
        "model_family": "weighted_strength",
        "description": "Distribui peso de forma mais equilibrada entre performance, mercado, FIFA e Elo.",
        "weights": {
            "recent_score": 0.22,
            "market_score": 0.18,
            "historical_score": 0.16,
            "fifa_score": 0.16,
            "elo_score": 0.16,
            "environment_score": 0.04,
            "socioeconomic_score": 0.08,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
    {
        "model_id": "recent_market_aggressive",
        "model_name": "Forma + mercado agressivo",
        "model_family": "weighted_strength",
        "description": "Prioriza forma recente e valor de mercado, reduzindo sinais macro.",
        "weights": {
            "recent_score": 0.45,
            "market_score": 0.35,
            "historical_score": 0.08,
            "fifa_score": 0.05,
            "elo_score": 0.04,
            "environment_score": 0.02,
            "socioeconomic_score": 0.01,
        },
        "probability_scale": 45,
        "draw_base": 0.28,
        "draw_diff_divisor": 230,
        "draw_floor": 0.16,
    },
    {
        "model_id": "fifa_elo_trust",
        "model_name": "FIFA + Elo",
        "model_family": "weighted_strength",
        "description": "Testa se ratings consolidados explicam melhor os resultados.",
        "weights": {
            "recent_score": 0.15,
            "market_score": 0.10,
            "historical_score": 0.10,
            "fifa_score": 0.25,
            "elo_score": 0.30,
            "environment_score": 0.02,
            "socioeconomic_score": 0.08,
        },
        "probability_scale": 45,
        "draw_base": 0.30,
        "draw_diff_divisor": 240,
        "draw_floor": 0.17,
    },
    {
        "model_id": "light_explanatory_model",
        "model_name": "Modelo explicativo leve",
        "model_family": "weighted_strength",
        "description": "Mantem Elo dominante e usa FIFA, forma, mercado e historico como apoio; socio/environment entram apenas como contexto leve.",
        "weights": {
            "recent_score": 0.15,
            "market_score": 0.10,
            "historical_score": 0.05,
            "fifa_score": 0.23,
            "elo_score": 0.45,
            "environment_score": 0.01,
            "socioeconomic_score": 0.01,
        },
        "probability_scale": 45,
        "draw_base": 0.30,
        "draw_diff_divisor": 240,
        "draw_floor": 0.17,
    },
    {
        "model_id": "lean_elo_fifa_model",
        "model_name": "Modelo Elo/FIFA enxuto",
        "model_family": "weighted_strength",
        "description": "Modelo compacto focado em Elo e FIFA, com pouco apoio de forma recente, mercado e historico.",
        "weights": {
            "recent_score": 0.12,
            "market_score": 0.07,
            "historical_score": 0.03,
            "fifa_score": 0.28,
            "elo_score": 0.50,
            "environment_score": 0.00,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 45,
        "draw_base": 0.30,
        "draw_diff_divisor": 240,
        "draw_floor": 0.17,
    },
    {
        "model_id": "socio_hdi_study",
        "model_name": "Estudo socioeconomico/IDH",
        "model_family": "weighted_strength",
        "description": "Aumenta o peso socioeconomico para estudar se IDH/PIB/expectativa de vida ajudam.",
        "weights": {
            "recent_score": 0.20,
            "market_score": 0.15,
            "historical_score": 0.12,
            "fifa_score": 0.10,
            "elo_score": 0.12,
            "environment_score": 0.06,
            "socioeconomic_score": 0.25,
        },
        "probability_scale": 55,
        "draw_base": 0.31,
        "draw_diff_divisor": 260,
        "draw_floor": 0.18,
    },
    {
        "model_id": "socio_economic_strong",
        "model_name": "Socio/IDH sem environment",
        "model_family": "ablation_study",
        "description": "Testa socioeconomico forte sem ajuda do componente ambiental.",
        "weights": {
            "recent_score": 0.20,
            "market_score": 0.20,
            "historical_score": 0.12,
            "fifa_score": 0.10,
            "elo_score": 0.23,
            "environment_score": 0.05,
            "socioeconomic_score": 0.10,
        },
        "probability_scale": 55,
        "draw_base": 0.31,
        "draw_diff_divisor": 260,
        "draw_floor": 0.18,
    },
    {
        "model_id": "environment_context",
        "model_name": "Contexto ambiental",
        "model_family": "weighted_strength",
        "description": "Dobra a aposta em adaptacao ambiental como diferencial competitivo.",
        "weights": {
            "recent_score": 0.22,
            "market_score": 0.18,
            "historical_score": 0.12,
            "fifa_score": 0.10,
            "elo_score": 0.12,
            "environment_score": 0.18,
            "socioeconomic_score": 0.08,
        },
        "probability_scale": 55,
        "draw_base": 0.31,
        "draw_diff_divisor": 260,
        "draw_floor": 0.18,
    },
    {
        "model_id": "environment_without_socio",
        "model_name": "Environment sem socioeconomico",
        "model_family": "ablation_study",
        "description": "Testa componente ambiental forte sem IDH/PIB/expectativa de vida.",
        "weights": {
            "recent_score": 0.22,
            "market_score": 0.18,
            "historical_score": 0.12,
            "fifa_score": 0.10,
            "elo_score": 0.12,
            "environment_score": 0.18,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 55,
        "draw_base": 0.31,
        "draw_diff_divisor": 260,
        "draw_floor": 0.18,
    },
    {
        "model_id": "recent_only_control",
        "model_name": "Controle: forma recente",
        "model_family": "single_signal_control",
        "description": "Modelo controle para medir o quanto a forma recente sozinha explica.",
        "weights": {
            "recent_score": 1.00,
            "market_score": 0.00,
            "historical_score": 0.00,
            "fifa_score": 0.00,
            "elo_score": 0.00,
            "environment_score": 0.00,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 55,
        "draw_base": 0.31,
        "draw_diff_divisor": 260,
        "draw_floor": 0.18,
    },
    {
        "model_id": "elo_only_control",
        "model_name": "Controle: Elo",
        "model_family": "single_signal_control",
        "description": "Modelo controle para medir o quanto Elo sozinho explica.",
        "weights": {
            "recent_score": 0.00,
            "market_score": 0.00,
            "historical_score": 0.00,
            "fifa_score": 0.00,
            "elo_score": 1.00,
            "environment_score": 0.00,
            "socioeconomic_score": 0.00,
        },
        "probability_scale": 50,
        "draw_base": 0.30,
        "draw_diff_divisor": 250,
        "draw_floor": 0.18,
    },
]

ABLATION_COMPARISONS = [
    {
        "comparison_id": "baseline_remove_socio",
        "base_model_id": "baseline_current",
        "variant_model_id": "baseline_without_socio",
        "comparison_label": "Baseline: remover socioeconomico",
    },
    {
        "comparison_id": "baseline_remove_environment",
        "base_model_id": "baseline_current",
        "variant_model_id": "baseline_without_environment",
        "comparison_label": "Baseline: remover environment",
    },
    {
        "comparison_id": "baseline_remove_both",
        "base_model_id": "baseline_current",
        "variant_model_id": "baseline_core_only",
        "comparison_label": "Baseline: remover socio + environment",
    },
    {
        "comparison_id": "socio_study_remove_environment",
        "base_model_id": "socio_hdi_study",
        "variant_model_id": "socio_hdi_without_environment",
        "comparison_label": "Socio/IDH: remover environment",
    },
    {
        "comparison_id": "environment_study_remove_socio",
        "base_model_id": "environment_context",
        "variant_model_id": "environment_without_socio",
        "comparison_label": "Environment: remover socioeconomico",
    },
]


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def postgres_type_for_series(series):
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE PRECISION"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "TEXT"


def ensure_table_columns(df, table_name, schema):
    inspector = inspect(engine)
    if not inspector.has_table(table_name, schema=schema):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(table_name, schema=schema)
    }
    missing_columns = [
        column
        for column in df.columns
        if column not in existing_columns
    ]

    if not missing_columns:
        return

    qualified_name = f"{quote_identifier(schema)}.{quote_identifier(table_name)}"
    with engine.begin() as conn:
        for column in missing_columns:
            column_type = postgres_type_for_series(df[column])
            conn.execute(
                text(
                    f"ALTER TABLE {qualified_name} "
                    f"ADD COLUMN {quote_identifier(column)} {column_type};"
                )
            )


def normalize_weights(weights):
    total = sum(float(weights.get(component, 0)) for component in COMPONENTS)
    if total <= 0:
        raise ValueError("A soma dos pesos do modelo precisa ser maior que zero.")

    return {
        component: float(weights.get(component, 0)) / total
        for component in COMPONENTS
    }


def model_catalog():
    rows = []
    for model in MODEL_CANDIDATES:
        weights = normalize_weights(model["weights"])
        row = {
            "model_id": model["model_id"],
            "model_name": model["model_name"],
            "model_family": model["model_family"],
            "description": model["description"],
            "probability_scale": model["probability_scale"],
            "draw_base": model["draw_base"],
            "draw_diff_divisor": model["draw_diff_divisor"],
            "draw_floor": model["draw_floor"],
        }
        row.update({f"weight_{component}": weight for component, weight in weights.items()})
        rows.append(row)

    return pd.DataFrame(rows)


def load_backtest_matches():
    query = """
    SELECT
        m.match_date,
        m.competition,
        m.home_team,
        m.away_team,
        m.home_score,
        m.away_score,
        m.city,
        m.country,
        m.neutral,
        m.data_source,

        hs.recent_score AS home_recent_score,
        aws.recent_score AS away_recent_score,
        hs.market_score AS home_market_score,
        aws.market_score AS away_market_score,
        hs.historical_score AS home_historical_score,
        aws.historical_score AS away_historical_score,
        hs.fifa_score AS home_fifa_score,
        aws.fifa_score AS away_fifa_score,
        hs.elo_score AS home_elo_score,
        aws.elo_score AS away_elo_score,
        hs.environment_score AS home_environment_score,
        aws.environment_score AS away_environment_score,
        hs.socioeconomic_score AS home_socioeconomic_score,
        aws.socioeconomic_score AS away_socioeconomic_score,

        hgp.attack_score AS home_attack_score,
        hgp.defense_score AS home_defense_score,
        agp.attack_score AS away_attack_score,
        agp.defense_score AS away_defense_score,

        CASE
            WHEN m.home_score > m.away_score THEN 'HOME_WIN'
            WHEN m.home_score = m.away_score THEN 'DRAW'
            WHEN m.home_score < m.away_score THEN 'AWAY_WIN'
        END AS actual_result

    FROM staging.matches_clean m
    INNER JOIN mart.team_strength_score hs
        ON m.home_team = hs.team_name
    INNER JOIN mart.team_strength_score aws
        ON m.away_team = aws.team_name
    LEFT JOIN mart.team_goal_profile hgp
        ON m.home_team = hgp.team_name
    LEFT JOIN mart.team_goal_profile agp
        ON m.away_team = agp.team_name
    WHERE m.home_score IS NOT NULL
      AND m.away_score IS NOT NULL
      AND m.home_team IS NOT NULL
      AND m.away_team IS NOT NULL
    """

    return pd.read_sql(text(query), engine)


def calculate_strength(row, side, weights):
    return sum(
        float(row.get(f"{side}_{component}", 0) or 0) * weight
        for component, weight in weights.items()
    )


def calculate_probabilities(strength_diff, model):
    expected_home = 1 / (1 + 10 ** (-strength_diff / model["probability_scale"]))

    draw_prob = model["draw_base"] - min(
        abs(strength_diff) / model["draw_diff_divisor"],
        model["draw_base"] - model["draw_floor"],
    )
    draw_prob = max(draw_prob, model["draw_floor"])

    remaining = 1 - draw_prob
    home_win_prob = expected_home * remaining
    away_win_prob = (1 - expected_home) * remaining

    return home_win_prob, draw_prob, away_win_prob


def predict_result(home_win_prob, draw_prob, away_win_prob):
    probabilities = {
        "HOME_WIN": home_win_prob,
        "DRAW": draw_prob,
        "AWAY_WIN": away_win_prob,
    }
    return max(probabilities, key=probabilities.get)


def result_from_goals(home_goals, away_goals):
    if home_goals > away_goals:
        return "HOME_WIN"
    if home_goals < away_goals:
        return "AWAY_WIN"
    return "DRAW"


def calculate_xg(row, strength_diff):
    base_home_xg = 1.45
    base_away_xg = 1.15

    home_attack = float(row.get("home_attack_score") or 50)
    away_attack = float(row.get("away_attack_score") or 50)
    home_defense = float(row.get("home_defense_score") or 50)
    away_defense = float(row.get("away_defense_score") or 50)

    home_attack_mult = 0.70 + (home_attack / 100) * 0.60
    away_attack_mult = 0.70 + (away_attack / 100) * 0.60
    away_defense_vulnerability = 1.30 - (away_defense / 100) * 0.60
    home_defense_vulnerability = 1.30 - (home_defense / 100) * 0.60

    home_strength_adj = max(min(1 + strength_diff / 250, 1.20), 0.80)
    away_strength_adj = max(min(1 - strength_diff / 250, 1.20), 0.80)

    home_xg = base_home_xg * home_attack_mult * away_defense_vulnerability * home_strength_adj
    away_xg = base_away_xg * away_attack_mult * home_defense_vulnerability * away_strength_adj

    return round(max(min(home_xg, 3.20), 0.25), 3), round(max(min(away_xg, 3.00), 0.25), 3)


def most_likely_score(home_xg, away_xg, max_goals=6):
    best_home_goals = 0
    best_away_goals = 0
    best_probability = -1

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = poisson_pmf(home_goals, home_xg) * poisson_pmf(away_goals, away_xg)
            if probability > best_probability:
                best_home_goals = home_goals
                best_away_goals = away_goals
                best_probability = probability

    return best_home_goals, best_away_goals, round(float(best_probability), 4)


def poisson_pmf(k, expected_goals):
    return (math.exp(-expected_goals) * expected_goals**k) / math.factorial(k)


def probability_for_actual_result(row):
    return {
        "HOME_WIN": row["home_win_prob"],
        "DRAW": row["draw_prob"],
        "AWAY_WIN": row["away_win_prob"],
    }[row["actual_result"]]


def brier_score(row):
    score = 0
    for result, column in [
        ("HOME_WIN", "home_win_prob"),
        ("DRAW", "draw_prob"),
        ("AWAY_WIN", "away_win_prob"),
    ]:
        actual = 1 if row["actual_result"] == result else 0
        score += (float(row[column]) - actual) ** 2
    return score


def build_predictions(matches):
    rows = []

    for model in MODEL_CANDIDATES:
        weights = normalize_weights(model["weights"])
        for _, match in matches.iterrows():
            home_strength = calculate_strength(match, "home", weights)
            away_strength = calculate_strength(match, "away", weights)
            strength_diff = home_strength - away_strength

            home_win_prob, draw_prob, away_win_prob = calculate_probabilities(strength_diff, model)
            predicted_result = predict_result(home_win_prob, draw_prob, away_win_prob)
            prediction_confidence = max(home_win_prob, draw_prob, away_win_prob)

            home_xg, away_xg = calculate_xg(match, strength_diff)
            predicted_home_goals, predicted_away_goals, score_probability = most_likely_score(
                home_xg,
                away_xg,
            )
            predicted_score_result = result_from_goals(
                predicted_home_goals,
                predicted_away_goals,
            )

            rows.append(
                {
                    "model_id": model["model_id"],
                    "model_name": model["model_name"],
                    "match_date": match["match_date"],
                    "competition": match["competition"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "home_score": int(match["home_score"]),
                    "away_score": int(match["away_score"]),
                    "actual_result": match["actual_result"],
                    "data_source": match["data_source"],
                    "home_model_strength": round(home_strength, 4),
                    "away_model_strength": round(away_strength, 4),
                    "strength_diff": round(strength_diff, 4),
                    "home_win_prob": round(home_win_prob, 4),
                    "draw_prob": round(draw_prob, 4),
                    "away_win_prob": round(away_win_prob, 4),
                    "predicted_result": predicted_result,
                    "prediction_confidence": round(prediction_confidence * 100, 2),
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "predicted_home_goals": predicted_home_goals,
                    "predicted_away_goals": predicted_away_goals,
                    "predicted_score": f"{predicted_home_goals}x{predicted_away_goals}",
                    "predicted_score_result": predicted_score_result,
                    "actual_score": f"{int(match['home_score'])}x{int(match['away_score'])}",
                    "predicted_score_prob": score_probability,
                }
            )

    predictions = pd.DataFrame(rows)
    predictions["result_hit"] = predictions["predicted_result"] == predictions["actual_result"]
    predictions["result_hit_with_draw"] = predictions["result_hit"]
    predictions["actual_draw"] = predictions["actual_result"] == "DRAW"
    predictions["draw_hit"] = np.where(
        predictions["actual_draw"],
        predictions["result_hit"],
        np.nan,
    )
    predictions["score_result_hit_with_draw"] = (
        predictions["predicted_score_result"] == predictions["actual_result"]
    )
    predictions["draw_hit_from_score"] = np.where(
        predictions["actual_draw"],
        predictions["score_result_hit_with_draw"],
        np.nan,
    )
    predictions["score_hit"] = (
        (predictions["predicted_home_goals"] == predictions["home_score"])
        & (predictions["predicted_away_goals"] == predictions["away_score"])
    )
    predictions["winner_hit_non_draw"] = np.where(
        predictions["actual_result"] == "DRAW",
        np.nan,
        predictions["result_hit"],
    )
    predictions["goal_mae"] = (
        (predictions["predicted_home_goals"] - predictions["home_score"]).abs()
        + (predictions["predicted_away_goals"] - predictions["away_score"]).abs()
    )
    predictions["goal_diff_mae"] = (
        (
            predictions["predicted_home_goals"]
            - predictions["predicted_away_goals"]
        )
        - (predictions["home_score"] - predictions["away_score"])
    ).abs()
    predictions["actual_result_probability"] = predictions.apply(probability_for_actual_result, axis=1)
    predictions["log_loss"] = -np.log(predictions["actual_result_probability"].clip(0.0001, 0.9999))
    predictions["brier_score"] = predictions.apply(brier_score, axis=1)

    return predictions


def summarize_predictions(predictions):
    summaries = []
    scopes = [
        ("all_matches", predictions),
        ("historical", predictions[predictions["data_source"] == "historical"]),
        ("worldcup_2026", predictions[predictions["data_source"] == "worldcup_2026"]),
    ]

    for scope_name, scope_df in scopes:
        if scope_df.empty:
            continue

        grouped = scope_df.groupby(["model_id", "model_name"], as_index=False).agg(
            matches_evaluated=("actual_result", "count"),
            result_accuracy=("result_hit", "mean"),
            result_accuracy_with_draw=("result_hit_with_draw", "mean"),
            result_accuracy_from_score_with_draw=("score_result_hit_with_draw", "mean"),
            winner_accuracy_non_draw=("winner_hit_non_draw", "mean"),
            draw_matches=("actual_draw", "sum"),
            draw_accuracy=("draw_hit", "mean"),
            draw_accuracy_from_score=("draw_hit_from_score", "mean"),
            exact_score_accuracy=("score_hit", "mean"),
            avg_goal_mae=("goal_mae", "mean"),
            avg_goal_diff_mae=("goal_diff_mae", "mean"),
            avg_log_loss=("log_loss", "mean"),
            avg_brier_score=("brier_score", "mean"),
            avg_prediction_confidence=("prediction_confidence", "mean"),
        )
        grouped["evaluation_scope"] = scope_name
        summaries.append(grouped)

    summary = pd.concat(summaries, ignore_index=True)
    summary["result_accuracy"] = (summary["result_accuracy"] * 100).round(2)
    summary["result_accuracy_with_draw"] = (
        summary["result_accuracy_with_draw"] * 100
    ).round(2)
    summary["result_accuracy_from_score_with_draw"] = (
        summary["result_accuracy_from_score_with_draw"] * 100
    ).round(2)
    summary["winner_accuracy_non_draw"] = (summary["winner_accuracy_non_draw"] * 100).round(2)
    summary["draw_accuracy"] = (summary["draw_accuracy"] * 100).round(2)
    summary["draw_accuracy_from_score"] = (
        summary["draw_accuracy_from_score"] * 100
    ).round(2)
    summary["draw_matches"] = summary["draw_matches"].astype(int)
    summary["exact_score_accuracy"] = (summary["exact_score_accuracy"] * 100).round(2)
    summary["avg_goal_mae"] = summary["avg_goal_mae"].round(3)
    summary["avg_goal_diff_mae"] = summary["avg_goal_diff_mae"].round(3)
    summary["avg_log_loss"] = summary["avg_log_loss"].round(4)
    summary["avg_brier_score"] = summary["avg_brier_score"].round(4)
    summary["avg_prediction_confidence"] = summary["avg_prediction_confidence"].round(2)

    summary = summary.sort_values(
        ["evaluation_scope", "result_accuracy", "avg_log_loss", "avg_goal_mae", "model_id"],
        ascending=[True, False, True, True, True],
    )
    summary["performance_rank"] = summary.groupby("evaluation_scope").cumcount() + 1

    return summary.sort_values(["evaluation_scope", "performance_rank", "model_id"])


def build_ablation_summary(summary):
    rows = []

    for comparison in ABLATION_COMPARISONS:
        for scope in summary["evaluation_scope"].unique():
            base = summary[
                (summary["evaluation_scope"] == scope)
                & (summary["model_id"] == comparison["base_model_id"])
            ]
            variant = summary[
                (summary["evaluation_scope"] == scope)
                & (summary["model_id"] == comparison["variant_model_id"])
            ]

            if base.empty or variant.empty:
                continue

            base_row = base.iloc[0]
            variant_row = variant.iloc[0]

            result_accuracy_delta = (
                variant_row["result_accuracy"] - base_row["result_accuracy"]
            )
            exact_score_accuracy_delta = (
                variant_row["exact_score_accuracy"] - base_row["exact_score_accuracy"]
            )
            avg_goal_mae_delta = variant_row["avg_goal_mae"] - base_row["avg_goal_mae"]
            avg_log_loss_delta = variant_row["avg_log_loss"] - base_row["avg_log_loss"]
            avg_brier_score_delta = (
                variant_row["avg_brier_score"] - base_row["avg_brier_score"]
            )

            rows.append(
                {
                    "comparison_id": comparison["comparison_id"],
                    "comparison_label": comparison["comparison_label"],
                    "evaluation_scope": scope,
                    "base_model_id": comparison["base_model_id"],
                    "base_model_name": base_row["model_name"],
                    "variant_model_id": comparison["variant_model_id"],
                    "variant_model_name": variant_row["model_name"],
                    "matches_evaluated": int(base_row["matches_evaluated"]),
                    "base_result_accuracy": base_row["result_accuracy"],
                    "variant_result_accuracy": variant_row["result_accuracy"],
                    "result_accuracy_delta": round(result_accuracy_delta, 2),
                    "base_exact_score_accuracy": base_row["exact_score_accuracy"],
                    "variant_exact_score_accuracy": variant_row["exact_score_accuracy"],
                    "exact_score_accuracy_delta": round(exact_score_accuracy_delta, 2),
                    "base_avg_goal_mae": base_row["avg_goal_mae"],
                    "variant_avg_goal_mae": variant_row["avg_goal_mae"],
                    "avg_goal_mae_delta": round(avg_goal_mae_delta, 3),
                    "base_avg_log_loss": base_row["avg_log_loss"],
                    "variant_avg_log_loss": variant_row["avg_log_loss"],
                    "avg_log_loss_delta": round(avg_log_loss_delta, 4),
                    "base_avg_brier_score": base_row["avg_brier_score"],
                    "variant_avg_brier_score": variant_row["avg_brier_score"],
                    "avg_brier_score_delta": round(avg_brier_score_delta, 4),
                    "variant_is_more_accurate": result_accuracy_delta > 0,
                    "variant_has_better_score_accuracy": exact_score_accuracy_delta > 0,
                    "variant_has_lower_goal_error": avg_goal_mae_delta < 0,
                    "variant_has_lower_log_loss": avg_log_loss_delta < 0,
                }
            )

    return pd.DataFrame(rows)


def create_experiment_views():
    with engine.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS experiments.vw_worldcup_model_results;"))
        conn.execute(text("DROP VIEW IF EXISTS experiments.vw_socio_environment_impact;"))
        conn.execute(text("DROP VIEW IF EXISTS experiments.vw_all_prediction_models;"))
        conn.execute(text("DROP VIEW IF EXISTS experiments.vw_best_prediction_models;"))
        conn.execute(text("DROP VIEW IF EXISTS experiments.vw_model_component_weights;"))

        conn.execute(
            text(
                """
                CREATE VIEW experiments.vw_all_prediction_models AS
                SELECT
                    s.evaluation_scope,
                    s.performance_rank,
                    s.model_id,
                    s.model_name,
                    c.model_family,
                    c.description,
                    s.matches_evaluated,
                    s.result_accuracy,
                    s.result_accuracy_with_draw,
                    s.result_accuracy_from_score_with_draw,
                    s.winner_accuracy_non_draw,
                    s.draw_matches,
                    s.draw_accuracy,
                    s.draw_accuracy_from_score,
                    s.exact_score_accuracy,
                    s.avg_goal_mae,
                    s.avg_goal_diff_mae,
                    s.avg_log_loss,
                    s.avg_brier_score,
                    s.avg_prediction_confidence,
                    c.weight_recent_score,
                    c.weight_market_score,
                    c.weight_historical_score,
                    c.weight_fifa_score,
                    c.weight_elo_score,
                    c.weight_environment_score,
                    c.weight_socioeconomic_score
                FROM experiments.model_evaluation_summary s
                LEFT JOIN experiments.model_candidates c
                    ON s.model_id = c.model_id
                ORDER BY s.evaluation_scope, s.performance_rank;
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE VIEW experiments.vw_best_prediction_models AS
                SELECT *
                FROM experiments.model_evaluation_summary
                WHERE performance_rank <= 5
                ORDER BY evaluation_scope, performance_rank;
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE VIEW experiments.vw_socio_environment_impact AS
                SELECT *
                FROM experiments.model_ablation_summary
                ORDER BY evaluation_scope, comparison_label;
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE VIEW experiments.vw_worldcup_model_results AS
                SELECT
                    model_id,
                    model_name,
                    match_date,
                    home_team,
                    away_team,
                    actual_score,
                    actual_result,
                    predicted_score,
                    predicted_score_result,
                    predicted_result,
                    result_hit,
                    result_hit_with_draw,
                    actual_draw,
                    draw_hit,
                    score_result_hit_with_draw,
                    draw_hit_from_score,
                    score_hit,
                    prediction_confidence,
                    home_win_prob,
                    draw_prob,
                    away_win_prob,
                    home_xg,
                    away_xg
                FROM experiments.model_match_predictions
                WHERE data_source = 'worldcup_2026'
                ORDER BY match_date DESC, model_name;
                """
            )
        )

        weight_columns = ", ".join(
            [
                f"('{' '.join(component.split('_')[:-1]).title()}', weight_{component})"
                for component in COMPONENTS
            ]
        )
        conn.execute(
            text(
                f"""
                CREATE VIEW experiments.vw_model_component_weights AS
                SELECT
                    model_id,
                    model_name,
                    component_name,
                    component_weight
                FROM experiments.model_candidates
                CROSS JOIN LATERAL (
                    VALUES {weight_columns}
                ) AS components(component_name, component_weight);
                """
            )
        )


def main():
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS experiments;"))

    catalog = model_catalog()
    matches = load_backtest_matches()

    if matches.empty:
        raise RuntimeError(
            "Nenhum jogo com placar e times mapeados foi encontrado para avaliar os modelos."
        )

    predictions = build_predictions(matches)
    summary = summarize_predictions(predictions)
    ablation_summary = build_ablation_summary(summary)

    ensure_table_columns(catalog, "model_candidates", "experiments")
    ensure_table_columns(predictions, "model_match_predictions", "experiments")
    ensure_table_columns(summary, "model_evaluation_summary", "experiments")
    ensure_table_columns(ablation_summary, "model_ablation_summary", "experiments")

    overwrite_table(catalog, "model_candidates", engine, schema="experiments", index=False)
    overwrite_table(predictions, "model_match_predictions", engine, schema="experiments", index=False)
    overwrite_table(summary, "model_evaluation_summary", engine, schema="experiments", index=False)
    overwrite_table(
        ablation_summary,
        "model_ablation_summary",
        engine,
        schema="experiments",
        index=False,
    )
    create_experiment_views()

    print("Modelos avaliados:")
    print(
        summary[summary["evaluation_scope"] == "all_matches"][
            [
                "performance_rank",
                "model_id",
                "matches_evaluated",
                "result_accuracy",
                "result_accuracy_with_draw",
                "result_accuracy_from_score_with_draw",
                "draw_accuracy",
                "draw_accuracy_from_score",
                "exact_score_accuracy",
                "avg_goal_mae",
                "avg_log_loss",
            ]
        ].head(10)
    )


if __name__ == "__main__":
    main()
