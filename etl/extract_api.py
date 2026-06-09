"""
extract_api.py — Extração da Remotive API.
Padrão de retry e paginação baseado no extract.py das aulas (etl_docker_python).
"""
import time
import logging
from typing import List, Dict, Any

import requests
import pandas as pd

from config import settings

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def fetch_jobs(category: str, limit: int, attempt: int = 1) -> List[Dict[str, Any]]:
    """Busca vagas na Remotive API com retry automático."""
    params = {"category": category, "limit": limit}

    for attempt in range(1, 4):
        try:
            log.info(f"[extract_api] tentativa {attempt}/3 — category={category}")
            response = requests.get(settings.remotive_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "jobs" not in data:
                raise ValueError("Resposta inesperada da API: campo 'jobs' ausente.")

            jobs = data["jobs"]
            log.info(f"[extract_api] {len(jobs)} vagas recebidas da API.")
            return jobs

        except Exception as exc:
            log.warning(f"[extract_api] tentativa {attempt} falhou: {exc}")
            time.sleep(2)

    raise RuntimeError("[extract_api] Falha ao extrair dados da API após 3 tentativas.")


def extract_api() -> pd.DataFrame:
    """
    Ponto de entrada principal.
    Retorna DataFrame com vagas da Remotive API.
    """
    # Busca em múltiplas categorias para enriquecer o dataset
    categorias = ["software-dev", "data", "devops-sysadmin"]
    todos = []

    for cat in categorias:
        try:
            jobs = fetch_jobs(category=cat, limit=100)
            for job in jobs:
                job["_categoria_busca"] = cat
            todos.extend(jobs)
        except Exception as exc:
            log.error(f"[extract_api] Erro na categoria '{cat}': {exc}")

    if not todos:
        log.warning("[extract_api] Nenhum dado extraído da API. Retornando DataFrame vazio.")
        return pd.DataFrame()

    df = pd.DataFrame(todos)

    # Seleciona e renomeia colunas relevantes
    colunas_map = {
        "id":                   "api_id",
        "url":                  "job_link",
        "title":                "job_title",
        "company_name":         "company",
        "candidate_required_location": "job_location",
        "job_type":             "job_type_api",
        "salary":               "salary_raw",
        "tags":                 "tags",
        "publication_date":     "first_seen",
        "_categoria_busca":     "categoria_busca",
    }

    colunas_existentes = {k: v for k, v in colunas_map.items() if k in df.columns}
    df = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    # Tags podem vir como lista — converter para string separada por vírgula
    if "tags" in df.columns:
        df["tags"] = df["tags"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x or "")
        )

    df["fonte"] = "remotive_api"
    log.info(f"[extract_api] DataFrame final: {df.shape[0]} linhas × {df.shape[1]} colunas.")
    return df


def run() -> pd.DataFrame:
    """Chamável pela DAG do Airflow."""
    return extract_api()
