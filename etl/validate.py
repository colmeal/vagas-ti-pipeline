"""
validate.py — Validações de qualidade de dados.
Implementa as 3+ regras:
nulos, duplicidades, ranges, integridade.
"""
import logging
from typing import Dict, Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def check_nulls(df: pd.DataFrame, colunas_criticas: list) -> Dict[str, Any]:
    """Regra 1 — Verifica nulos em colunas críticas."""
    resultado = {}
    for col in colunas_criticas:
        if col not in df.columns:
            continue
        n_nulos = df[col].isnull().sum()
        pct     = round(n_nulos / len(df) * 100, 2) if len(df) > 0 else 0
        resultado[col] = {"nulos": int(n_nulos), "pct": pct}
        if n_nulos > 0:
            log.warning(f"[validate] NULOS — coluna '{col}': {n_nulos} ({pct}%)")

    return resultado


def check_duplicates(df: pd.DataFrame, subset: list) -> Dict[str, Any]:
    """Regra 2 — Verifica registros duplicados."""
    cols_presentes = [c for c in subset if c in df.columns]
    if not cols_presentes:
        return {"duplicados": 0, "subset": []}

    n_dup = df.duplicated(subset=cols_presentes).sum()
    pct   = round(n_dup / len(df) * 100, 2) if len(df) > 0 else 0

    if n_dup > 0:
        log.warning(f"[validate] DUPLICADOS — {n_dup} ({pct}%) registros duplicados em {cols_presentes}.")
    else:
        log.info(f"[validate] Sem duplicatas em {cols_presentes}.")

    return {"duplicados": int(n_dup), "pct": pct, "subset": cols_presentes}


def check_salary_range(df: pd.DataFrame) -> Dict[str, Any]:
    """Regra 3 — Valida consistência de faixas salariais."""
    if "salario_min" not in df.columns or "salario_max" not in df.columns:
        return {"status": "colunas_ausentes"}

    invalidos = df[
        df["salario_min"].notna() &
        df["salario_max"].notna() &
        (df["salario_min"] > df["salario_max"])
    ]

    n = len(invalidos)
    if n > 0:
        log.warning(f"[validate] SALÁRIO INVÁLIDO — {n} registros com min > max.")
    else:
        log.info("[validate] Faixas salariais consistentes.")

    return {"salarios_invalidos": n}


def check_date_range(df: pd.DataFrame, col: str = "first_seen") -> Dict[str, Any]:
    """Regra 4 — Verifica datas fora de intervalo razoável (2020–2026)."""
    if col not in df.columns:
        return {"status": "coluna_ausente"}

    datas = pd.to_datetime(df[col], errors="coerce")
    invalidas = datas[
        datas.notna() & ((datas.dt.year < 2020) | (datas.dt.year > 2026))
    ]

    n = len(invalidas)
    if n > 0:
        log.warning(f"[validate] DATAS INVÁLIDAS — {n} registros fora de 2020-2026.")

    return {"datas_invalidas": n}


def check_empty_strings(df: pd.DataFrame, colunas: list) -> Dict[str, Any]:
    """Regra 5 — Detecta strings vazias disfarçadas de dados."""
    resultado = {}
    for col in colunas:
        if col not in df.columns:
            continue
        n = (df[col].astype(str).str.strip() == "").sum()
        if n > 0:
            log.warning(f"[validate] STRINGS VAZIAS — coluna '{col}': {n} registros.")
        resultado[col] = int(n)
    return resultado


def validate_dataframe(df: pd.DataFrame, fonte: str = "desconhecida") -> Dict[str, Any]:
    """
    Executa todas as regras de validação sobre um DataFrame.
    Retorna dicionário com métricas de qualidade.
    """
    log.info(f"[validate] Iniciando validação — fonte='{fonte}', shape={df.shape}")

    relatorio = {
        "fonte":       fonte,
        "total_linhas": len(df),
        "nulos":       check_nulls(df, ["job_title", "company", "first_seen"]),
        "duplicados":  check_duplicates(df, ["job_title", "company"]),
        "datas":       check_date_range(df, "first_seen"),
        "strings_vazias": check_empty_strings(df, ["job_title", "company"]),
    }

    # Só checa salário se existir
    if "salario_min" in df.columns:
        relatorio["salarios"] = check_salary_range(df)

    # Score simples de qualidade (0–100)
    penalidades = 0
    dup_pct  = relatorio["duplicados"].get("pct", 0)
    penalidades += min(dup_pct, 30)  # max 30 pts por duplicatas

    for col, info in relatorio["nulos"].items():
        penalidades += min(info["pct"], 10)  # max 10 pts por coluna nula

    relatorio["dq_score"] = max(0, round(100 - penalidades, 1))

    log.info(
        f"[validate] Validação concluída — fonte='{fonte}' | "
        f"duplicados={relatorio['duplicados']['duplicados']} | "
        f"DQ Score={relatorio['dq_score']}"
    )
    return relatorio


def run(df_api: pd.DataFrame, df_csv: pd.DataFrame) -> dict:
    """Chamável pela DAG do Airflow."""
    rel_api = validate_dataframe(df_api, fonte="remotive_api")
    rel_csv = validate_dataframe(df_csv, fonte="csv_dataset")
    return {"api": rel_api, "csv": rel_csv}
