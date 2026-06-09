"""
extract_json.py — Carrega stacks_map.json (fonte semi-estruturada local).
Constrói a taxonomia de tecnologias usada para enriquecer os dados.
"""
import json
import logging
from typing import Optional

import pandas as pd

from config import settings

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def extract_json(path: Optional[str] = None) -> pd.DataFrame:
    """
    Carrega stacks_map.json e retorna DataFrame com taxonomia de tecnologias.
    Usado para enriquecer a dim_tecnologia no pipeline.
    """
    json_path = path or settings.json_path

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("[extract_json] stacks_map.json deve ser uma lista de objetos.")

    df = pd.DataFrame(data)

    # Valida colunas obrigatórias
    obrigatorias = {"skill", "categoria", "area"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"[extract_json] Colunas ausentes no JSON: {faltando}")

    # Normaliza: strip e title case na skill
    df["skill"]      = df["skill"].str.strip()
    df["categoria"]  = df["categoria"].str.strip()
    df["area"]       = df["area"].str.strip()

    # Cria lookup dict para uso no transform.py
    # { "python": {"categoria": "Backend", "area": "Dados"}, ... }
    log.info(f"[extract_json] {len(df)} tecnologias carregadas da taxonomia.")
    return df


def build_lookup(df: pd.DataFrame) -> dict:
    """
    Constrói dicionário de lookup {skill_lower: {categoria, area}}
    para uso rápido no transform.py.
    """
    lookup = {}
    for _, row in df.iterrows():
        lookup[row["skill"].lower()] = {
            "categoria": row["categoria"],
            "area":      row["area"],
        }
    return lookup


def run() -> pd.DataFrame:
    """Chamável pela DAG do Airflow."""
    return extract_json()
