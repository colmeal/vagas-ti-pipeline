"""
extract_csv.py — Extração do dataset job_postings.csv.
Fonte estruturada principal com ~12k vagas reais de tecnologia.
"""
import logging
from typing import Optional

import pandas as pd

from config import settings

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Colunas que importam para o projeto
COLUNAS_UTEIS = [
    "job_link",
    "job_title",
    "company",
    "job_location",
    "first_seen",
    "search_country",
    "job_level",
    "job_type",
]


def extract_csv(path: Optional[str] = None) -> pd.DataFrame:
    """
    Carrega job_postings.csv, padroniza colunas e trata inconsistências básicas.
    Retorna DataFrame pronto para validação.
    """
    csv_path = path or settings.csv_path

    try:
        df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
        log.info(f"[extract_csv] Arquivo carregado: {df.shape[0]} linhas × {df.shape[1]} colunas.")
    except UnicodeDecodeError:
        log.warning("[extract_csv] UTF-8 falhou. Tentando latin-1.")
        df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False)

    # Seleciona apenas colunas úteis (ignora metadados internos do dataset)
    colunas_presentes = [c for c in COLUNAS_UTEIS if c in df.columns]
    df = df[colunas_presentes].copy()

    # Padroniza nomes de colunas: lower + sem espaços
    df.columns = [c.lower().strip() for c in df.columns]

    # Padroniza strings: strip de espaços
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Converte first_seen para datetime, aceita formatos variados
    if "first_seen" in df.columns:
        df["first_seen"] = pd.to_datetime(df["first_seen"], errors="coerce")

    # Padroniza job_type para inglês consistente
    if "job_type" in df.columns:
        mapping_tipo = {
            "onsite": "Onsite",
            "remote": "Remote",
            "hybrid": "Hybrid",
        }
        df["job_type"] = df["job_type"].str.lower().map(mapping_tipo).fillna("Onsite")

    # Padroniza job_level
    if "job_level" in df.columns:
        mapping_nivel = {
            "mid senior": "Mid-Senior",
            "associate":  "Associate",
            "entry level": "Entry Level",
            "director":   "Director",
            "executive":  "Executive",
        }
        df["job_level"] = (
            df["job_level"]
            .str.lower()
            .map(mapping_nivel)
            .fillna("Not Specified")
        )

    df["fonte"] = "csv_dataset"
    log.info(f"[extract_csv] DataFrame final: {df.shape[0]} linhas × {df.shape[1]} colunas.")
    return df


def run() -> pd.DataFrame:
    """Chamável pela DAG do Airflow."""
    return extract_csv()
