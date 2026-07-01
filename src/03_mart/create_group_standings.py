import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH team_groups AS (
    SELECT *
    FROM (VALUES
        ('A', 'Mexico'),
        ('A', 'South Africa'),
        ('A', 'South Korea'),
        ('A', 'Czech Republic'),

        ('B', 'Canada'),
        ('B', 'Bosnia & Herzegovina'),
        ('B', 'Qatar'),
        ('B', 'Switzerland'),

        ('C', 'Brazil'),
        ('C', 'Morocco'),
        ('C', 'Haiti'),
        ('C', 'Scotland'),

        ('D', 'USA'),
        ('D', 'Paraguay'),
        ('D', 'Australia'),
        ('D', 'Turkey'),

        ('E', 'Germany'),
        ('E', 'Curaçao'),
        ('E', 'Ivory Coast'),
        ('E', 'Ecuador'),

        ('F', 'Netherlands'),
        ('F', 'Japan'),
        ('F', 'Sweden'),
        ('F', 'Tunisia'),

        ('G', 'Belgium'),
        ('G', 'Egypt'),
        ('G', 'Iran'),
        ('G', 'New Zealand'),

        ('H', 'Spain'),
        ('H', 'Cape Verde'),
        ('H', 'Saudi Arabia'),
        ('H', 'Uruguay'),

        ('I', 'France'),
        ('I', 'Senegal'),
        ('I', 'Iraq'),
        ('I', 'Norway'),

        ('J', 'Argentina'),
        ('J', 'Algeria'),
        ('J', 'Austria'),
        ('J', 'Jordan'),

        ('K', 'Portugal'),
        ('K', 'DR Congo'),
        ('K', 'Uzbekistan'),
        ('K', 'Colombia'),

        ('L', 'England'),
        ('L', 'Croatia'),
        ('L', 'Ghana'),
        ('L', 'Panama')
    ) AS t(group_name, team_name)
),

matches AS (
    SELECT
        w.data::date AS match_date,
        w.rodada,
        w.time_casa AS home_team_raw,
        w.time_fora AS away_team_raw,
        w.gols_casa,
        w.gols_fora,
        w.status
    FROM raw.worldcup_matches w
    WHERE LOWER(w.status) IN ('finalizado', 'complete', 'completed')
      AND w.gols_casa IS NOT NULL
      AND w.gols_fora IS NOT NULL
),

mapped AS (
    SELECT
        m.match_date,

        CASE
            WHEN COALESCE(mh.canonical_name, m.home_team_raw) IN ('United States', 'Estados Unidos') THEN 'USA'
            WHEN COALESCE(mh.canonical_name, m.home_team_raw) IN ('Czechia', 'Tchéquia') THEN 'Czech Republic'
            WHEN COALESCE(mh.canonical_name, m.home_team_raw) IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina', 'Bósnia-Herzegovina') THEN 'Bosnia & Herzegovina'
            ELSE COALESCE(mh.canonical_name, m.home_team_raw)
        END AS home_team,

        CASE
            WHEN COALESCE(ma.canonical_name, m.away_team_raw) IN ('United States', 'Estados Unidos') THEN 'USA'
            WHEN COALESCE(ma.canonical_name, m.away_team_raw) IN ('Czechia', 'Tchéquia') THEN 'Czech Republic'
            WHEN COALESCE(ma.canonical_name, m.away_team_raw) IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina', 'Bósnia-Herzegovina') THEN 'Bosnia & Herzegovina'
            ELSE COALESCE(ma.canonical_name, m.away_team_raw)
        END AS away_team,

        m.gols_casa,
        m.gols_fora
    FROM matches m
    LEFT JOIN staging.team_mapping mh
        ON m.home_team_raw = mh.team_name
    LEFT JOIN staging.team_mapping ma
        ON m.away_team_raw = ma.team_name
),

team_rows AS (
    SELECT
        tg.group_name,
        m.home_team AS team_name,
        1 AS played,
        CASE WHEN m.gols_casa > m.gols_fora THEN 1 ELSE 0 END AS wins,
        CASE WHEN m.gols_casa = m.gols_fora THEN 1 ELSE 0 END AS draws,
        CASE WHEN m.gols_casa < m.gols_fora THEN 1 ELSE 0 END AS losses,
        m.gols_casa AS goals_for,
        m.gols_fora AS goals_against,
        CASE
            WHEN m.gols_casa > m.gols_fora THEN 3
            WHEN m.gols_casa = m.gols_fora THEN 1
            ELSE 0
        END AS points
    FROM mapped m
    INNER JOIN team_groups tg
        ON m.home_team = tg.team_name

    UNION ALL

    SELECT
        tg.group_name,
        m.away_team AS team_name,
        1 AS played,
        CASE WHEN m.gols_fora > m.gols_casa THEN 1 ELSE 0 END AS wins,
        CASE WHEN m.gols_fora = m.gols_casa THEN 1 ELSE 0 END AS draws,
        CASE WHEN m.gols_fora < m.gols_casa THEN 1 ELSE 0 END AS losses,
        m.gols_fora AS goals_for,
        m.gols_casa AS goals_against,
        CASE
            WHEN m.gols_fora > m.gols_casa THEN 3
            WHEN m.gols_fora = m.gols_casa THEN 1
            ELSE 0
        END AS points
    FROM mapped m
    INNER JOIN team_groups tg
        ON m.away_team = tg.team_name
),

standings AS (
    SELECT
        group_name,
        team_name,
        SUM(played) AS played,
        SUM(wins) AS wins,
        SUM(draws) AS draws,
        SUM(losses) AS losses,
        SUM(goals_for) AS goals_for,
        SUM(goals_against) AS goals_against,
        SUM(goals_for) - SUM(goals_against) AS goal_difference,
        SUM(points) AS points
    FROM team_rows
    GROUP BY group_name, team_name
),

full_standings AS (
    SELECT
        tg.group_name,
        tg.team_name,
        COALESCE(s.played, 0) AS played,
        COALESCE(s.wins, 0) AS wins,
        COALESCE(s.draws, 0) AS draws,
        COALESCE(s.losses, 0) AS losses,
        COALESCE(s.goals_for, 0) AS goals_for,
        COALESCE(s.goals_against, 0) AS goals_against,
        COALESCE(s.goal_difference, 0) AS goal_difference,
        COALESCE(s.points, 0) AS points
    FROM team_groups tg
    LEFT JOIN standings s
        ON tg.group_name = s.group_name
       AND tg.team_name = s.team_name
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY group_name
            ORDER BY
                points DESC,
                goal_difference DESC,
                goals_for DESC,
                wins DESC,
                team_name ASC
        ) AS group_position
    FROM full_standings
)

SELECT
    group_name,
    group_position,
    team_name,
    played,
    wins,
    draws,
    losses,
    goals_for,
    goals_against,
    goal_difference,
    points,

    CASE
        WHEN group_position <= 2 THEN 'CLASSIFICATION_ZONE'
        ELSE 'RISK_ZONE'
    END AS qualification_status

FROM ranked
ORDER BY group_name, group_position
"""

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)

overwrite_table(

    df,
    "group_standings",
    engine,
    schema="mart",
    index=False
)

print(df)
print(f"{len(df)} linhas carregadas em mart.group_standings")