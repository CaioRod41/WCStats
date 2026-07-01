from sqlalchemy import create_engine, text

from config import *


engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

sql = """
CREATE TABLE IF NOT EXISTS mart.match_extra_info (
    match_key TEXT PRIMARY KEY,
    stadium TEXT,
    city TEXT,
    host_country TEXT
);

DROP VIEW IF EXISTS mart.vw_next_match_score_probabilities;
DROP VIEW IF EXISTS mart.vw_next_match;
DROP VIEW IF EXISTS mart.vw_match_center;

CREATE VIEW mart.vw_match_center AS
WITH team_groups AS (
    SELECT
        group_name,
        team_name,
        team_name_pt,
        iso2
    FROM raw.worldcup_teams
),

mapped_matches AS (
    SELECT
        w.data::date AS match_date,
        w.hora AS match_time,
        w.rodada,
        w.status,
        w.time_casa AS home_team_source,
        w.time_fora AS away_team_source,

        CASE
            WHEN COALESCE(mh.canonical_name, w.time_casa) IN ('United States', 'Estados Unidos') THEN 'USA'
            WHEN COALESCE(mh.canonical_name, w.time_casa) IN ('Czechia', 'Tchequia') THEN 'Czech Republic'
            WHEN COALESCE(mh.canonical_name, w.time_casa) IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina') THEN 'Bosnia & Herzegovina'
            ELSE COALESCE(mh.canonical_name, w.time_casa)
        END AS home_team,

        CASE
            WHEN COALESCE(ma.canonical_name, w.time_fora) IN ('United States', 'Estados Unidos') THEN 'USA'
            WHEN COALESCE(ma.canonical_name, w.time_fora) IN ('Czechia', 'Tchequia') THEN 'Czech Republic'
            WHEN COALESCE(ma.canonical_name, w.time_fora) IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina') THEN 'Bosnia & Herzegovina'
            ELSE COALESCE(ma.canonical_name, w.time_fora)
        END AS away_team,

        w.gols_casa AS home_goals,
        w.gols_fora AS away_goals

    FROM raw.worldcup_matches w

    LEFT JOIN staging.team_mapping mh
        ON w.time_casa = mh.team_name

    LEFT JOIN staging.team_mapping ma
        ON w.time_fora = ma.team_name
),

base AS (
    SELECT
        m.*,

        COALESCE(hg.group_name, ag.group_name) AS group_name,
        'Grupo ' || COALESCE(hg.group_name, ag.group_name) AS group_label,
        m.rodada::text AS source_round_label,
        COALESCE(hg.team_name_pt, m.home_team_source, m.home_team) AS home_team_pt,
        COALESCE(ag.team_name_pt, m.away_team_source, m.away_team) AS away_team_pt,

        hg.iso2 AS home_iso2,
        ag.iso2 AS away_iso2,

        'https://flagcdn.com/w320/' || hg.iso2 || '.png' AS home_flag_url,
        'https://flagcdn.com/w320/' || ag.iso2 || '.png' AS away_flag_url,

        to_char(m.match_date, 'YYYY-MM-DD') || '|' || m.home_team || '|' || m.away_team AS match_key,
        m.home_team || ' x ' || m.away_team AS match_label,
        COALESCE(hg.team_name_pt, m.home_team_source, m.home_team) || ' x ' ||
            COALESCE(ag.team_name_pt, m.away_team_source, m.away_team) AS match_label_pt,
        COALESCE(hg.team_name_pt, m.home_team_source, m.home_team) || ' x ' ||
            COALESCE(ag.team_name_pt, m.away_team_source, m.away_team) AS match_label_full_pt

    FROM mapped_matches m

    LEFT JOIN team_groups hg
        ON m.home_team = hg.team_name

    LEFT JOIN team_groups ag
        ON m.away_team = ag.team_name
),

ranked_base AS (
    SELECT
        b.*,
        CEIL(
            ROW_NUMBER() OVER (
                PARTITION BY b.group_name
                ORDER BY b.match_date, b.match_time NULLS LAST, b.match_label
            )::numeric / 2
        )::int AS group_round_number
    FROM base b
),

match_enriched AS (
    SELECT
        b.*,
        COALESCE(extra.stadium, 'A definir') AS stadium,
        COALESCE(extra.city, 'A definir') AS city,
        COALESCE(extra.host_country, 'A definir') AS host_country_raw,
        CASE
            WHEN LOWER(COALESCE(extra.city, '')) IN (
                'atlanta', 'boston', 'east rutherford', 'foxborough', 'miami',
                'new york', 'new york new jersey', 'orlando', 'philadelphia',
                'toronto', 'washington', 'washington dc'
            ) THEN 1
            WHEN LOWER(COALESCE(extra.city, '')) IN (
                'arlington', 'dallas', 'houston', 'kansas city'
            ) THEN 2
            WHEN LOWER(COALESCE(extra.city, '')) IN (
                'guadalajara', 'mexico city', 'ciudad de mexico', 'ciudad de méxico', 'monterrey'
            ) THEN 3
            WHEN LOWER(COALESCE(extra.city, '')) IN (
                'los angeles', 'san francisco', 'santa clara', 'seattle', 'vancouver'
            ) THEN 4
            ELSE 0
        END AS br_time_offset_hours
    FROM ranked_base b

    LEFT JOIN mart.match_extra_info extra
        ON b.match_key = extra.match_key
)

SELECT
    b.match_key,
    b.match_label,
    b.match_label_pt,
    b.match_label_full_pt,

    b.match_date,
    b.match_time,
    to_char(
        (
            CASE
                WHEN b.match_time IS NULL OR TRIM(b.match_time::text) = '' THEN b.match_date::timestamp
                ELSE (b.match_date::text || ' ' || LEFT(b.match_time::text, 5))::timestamp
            END
            + (b.br_time_offset_hours || ' hours')::interval
        ),
        'DD/MM/YYYY'
    ) AS match_date_br_label,
    CASE
        WHEN b.match_time IS NULL OR TRIM(b.match_time::text) = '' THEN NULL
        ELSE to_char(
            (
                (b.match_date::text || ' ' || LEFT(b.match_time::text, 5))::timestamp
                + (b.br_time_offset_hours || ' hours')::interval
            ),
            'HH24:MI'
        )
    END AS match_time_br_label,
    CASE
        WHEN b.match_time IS NULL OR TRIM(b.match_time::text) = '' THEN to_char(b.match_date, 'DD/MM/YYYY')
        ELSE to_char(
            (
                (b.match_date::text || ' ' || LEFT(b.match_time::text, 5))::timestamp
                + (b.br_time_offset_hours || ' hours')::interval
            ),
            'DD/MM/YYYY'
        ) || ' • ' || to_char(
            (
                (b.match_date::text || ' ' || LEFT(b.match_time::text, 5))::timestamp
                + (b.br_time_offset_hours || ' hours')::interval
            ),
            'HH24:MI'
        )
    END AS match_datetime_br_label,

    b.rodada,
    b.source_round_label,
    b.group_round_number,
    b.group_round_number::text || 'ª Rodada' AS round_label,
    b.group_round_number::text || 'ª Rodada' AS round_label_pt,
    b.group_name,
    b.group_label,
    b.status,

    'FIFA World Cup 2026' AS competition,

    b.home_team,
    b.away_team,
    b.home_team_pt,
    b.away_team_pt,

    b.home_goals,
    b.away_goals,

    b.home_flag_url,
    b.away_flag_url,

    hs.fifa_rank AS home_fifa_rank,
    aws.fifa_rank AS away_fifa_rank,

    hs.team_strength_score AS home_strength_score,
    aws.team_strength_score AS away_strength_score,

    hs.elo_rating AS home_elo_rating,
    aws.elo_rating AS away_elo_rating,

    sp.home_win_prob,
    sp.draw_prob,
    sp.away_win_prob,
    ROUND((sp.home_win_prob * 100)::numeric, 2) AS home_win_prob_pct,
    ROUND((sp.draw_prob * 100)::numeric, 2) AS draw_prob_pct,
    ROUND((sp.away_win_prob * 100)::numeric, 2) AS away_win_prob_pct,
    sp.favorite_team,
    sp.prediction_confidence,

    sp.home_xg,
    sp.away_xg,
    sp.total_xg,

    sp.most_likely_score,
    sp.most_likely_score_prob,

    sp.top_1_score,
    sp.top_1_score_prob,
    sp.top_2_score,
    sp.top_2_score_prob,
    sp.top_3_score,
    sp.top_3_score_prob,
    sp.top_4_score,
    sp.top_4_score_prob,
    sp.top_5_score,
    sp.top_5_score_prob,

    sp.btts_prob,
    ROUND((sp.btts_prob * 100)::numeric, 2) AS btts_prob_pct,
    sp.over_1_5_prob,
    sp.over_2_5_prob,
    sp.over_3_5_prob,
    sp.under_2_5_prob,
    ROUND((sp.over_1_5_prob * 100)::numeric, 2) AS over_1_5_prob_pct,
    ROUND((sp.over_2_5_prob * 100)::numeric, 2) AS over_2_5_prob_pct,
    ROUND((sp.over_3_5_prob * 100)::numeric, 2) AS over_3_5_prob_pct,
    ROUND((sp.under_2_5_prob * 100)::numeric, 2) AS under_2_5_prob_pct,

    b.stadium,
    b.city,
    b.host_country_raw,
    CASE
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('usa', 'united states', 'united states of america') THEN 'Estados Unidos'
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('mexico', 'méxico') THEN 'México'
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('canada', 'canadá') THEN 'Canadá'
        ELSE COALESCE(b.host_country_raw, 'A definir')
    END AS host_country,
    CASE
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('usa', 'united states', 'united states of america') THEN 'Estados Unidos'
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('mexico', 'méxico') THEN 'México'
        WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('canada', 'canadá') THEN 'Canadá'
        ELSE COALESCE(b.host_country_raw, 'A definir')
    END AS host_country_pt,
    b.city || ', ' ||
        CASE
            WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('usa', 'united states', 'united states of america') THEN 'Estados Unidos'
            WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('mexico', 'méxico') THEN 'México'
            WHEN LOWER(COALESCE(b.host_country_raw, '')) IN ('canada', 'canadá') THEN 'Canadá'
            ELSE COALESCE(b.host_country_raw, 'A definir')
        END AS city_country_label_pt

FROM match_enriched b

LEFT JOIN mart.team_strength_score hs
    ON b.home_team = hs.team_name

LEFT JOIN mart.team_strength_score aws
    ON b.away_team = aws.team_name

LEFT JOIN mart.score_probabilities sp
    ON b.match_date = sp.match_date
   AND b.home_team = sp.home_team
   AND b.away_team = sp.away_team;

CREATE OR REPLACE VIEW mart.vw_next_match AS
SELECT *
FROM mart.vw_match_center
WHERE LOWER(status) IN ('agendado', 'scheduled')
  AND match_date >= CURRENT_DATE
ORDER BY match_date, match_time NULLS LAST, match_label
LIMIT 2;

CREATE OR REPLACE VIEW mart.vw_next_match_score_probabilities AS
SELECT
    n.match_key,
    n.match_label,
    n.match_label_pt,
    n.match_label_full_pt,
    n.match_date,
    n.match_time,
    n.match_date_br_label,
    n.match_time_br_label,
    n.match_datetime_br_label,
    n.group_name,
    n.group_label,
    n.round_label,
    n.round_label_pt,
    n.home_team,
    n.away_team,
    n.home_team_pt,
    n.away_team_pt,
    n.home_win_prob,
    n.draw_prob,
    n.away_win_prob,
    n.favorite_team,
    n.prediction_confidence,
    n.home_xg,
    n.away_xg,
    n.total_xg,
    n.most_likely_score,
    n.most_likely_score_prob,
    n.top_1_score,
    n.top_1_score_prob,
    n.top_2_score,
    n.top_2_score_prob,
    n.top_3_score,
    n.top_3_score_prob,
    n.top_4_score,
    n.top_4_score_prob,
    n.top_5_score,
    n.top_5_score_prob,
    n.btts_prob,
    n.over_1_5_prob,
    n.over_2_5_prob,
    n.over_3_5_prob,
    n.under_2_5_prob,
    s.score_rank,
    s.score,
    s.score_prob,
    ROUND((s.score_prob * 100)::numeric, 2) AS score_prob_pct
FROM mart.vw_next_match n
CROSS JOIN LATERAL (
    VALUES
        (1, n.top_1_score, n.top_1_score_prob),
        (2, n.top_2_score, n.top_2_score_prob),
        (3, n.top_3_score, n.top_3_score_prob),
        (4, n.top_4_score, n.top_4_score_prob),
        (5, n.top_5_score, n.top_5_score_prob)
) AS s(score_rank, score, score_prob)
WHERE s.score IS NOT NULL
ORDER BY n.match_date, n.match_time NULLS LAST, n.match_label, s.score_rank;

CREATE OR REPLACE VIEW mart.vw_team_power_ranking AS
SELECT
    ROW_NUMBER() OVER (
        ORDER BY tss.team_strength_score DESC NULLS LAST
    ) AS strength_rank,

    tss.team_name,
    dc.iso3,
    dc.is_world_cup_team,

    tss.team_strength_score,
    tss.recent_score,
    tss.historical_score,
    tss.market_score,
    tss.fifa_score,
    tss.environment_score,
    tss.elo_score,
    tss.socioeconomic_score,

    tss.recent_ppg,
    tss.historical_ppg,
    tss.market_value_eur,
    tss.fifa_rank,
    tss.fifa_points,
    tss.elo_rating,

    tmv.players_count,
    tmv.avg_age,
    tmv.avg_market_value_eur,

    tci.gdp_per_capita_current_usd,
    tci.life_expectancy,
    tci.population_total,
    th.hdi,

    tep.avg_temperature_annual,
    tep.avg_humidity_annual,
    tep.avg_elevation_meters,

    'https://flagcdn.com/w320/' || wt.iso2 || '.png' AS flag_url,
    wt.group_name

FROM mart.team_strength_score tss

LEFT JOIN mart.dim_country dc
    ON tss.team_name = dc.country_name

LEFT JOIN mart.team_market_value tmv
    ON tss.team_name = tmv.team_name

LEFT JOIN mart.team_country_indicators tci
    ON tss.team_name = tci.team_name

LEFT JOIN mart.team_hdi th
    ON tss.team_name = th.team_name

LEFT JOIN mart.team_environment_profile tep
    ON tss.team_name = tep.team_name

LEFT JOIN raw.worldcup_teams wt
    ON tss.team_name = wt.team_name

ORDER BY strength_rank;
"""

with engine.begin() as conn:
    conn.execute(text(sql))

print("Views mart.vw_match_center, mart.vw_next_match, mart.vw_next_match_score_probabilities e mart.vw_team_power_ranking atualizadas.")
print("Tabela mart.match_extra_info criada/verificada.")
