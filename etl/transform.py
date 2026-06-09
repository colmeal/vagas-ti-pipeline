"""
transform.py — Transformações ETL centralizadas.
Normaliza, enriquece e prepara dados para carga dimensional.
"""
import re
import logging
from typing import Optional, Tuple
from datetime import date

import pandas as pd

from extract_json import build_lookup

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Funções auxiliares (safe helpers — padrão das aulas)
# -------------------------------------------------------------------

def safe_str(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def safe_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


# -------------------------------------------------------------------
# Normalização salarial
# -------------------------------------------------------------------

def parse_salary(salary_raw: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extrai salário mínimo e máximo de strings como:
    "$80,000 - $120,000", "80k-120k", "up to $150k", etc.
    Retorna (salario_min, salario_max) em USD anuais.
    """
    if not salary_raw or pd.isna(salary_raw):
        return None, None

    text = str(salary_raw).replace(",", "").replace("$", "").lower().strip()

    # Converte "k" para milhares
    text = re.sub(r"(\d+\.?\d*)k", lambda m: str(float(m.group(1)) * 1000), text)

    numeros = re.findall(r"\d+\.?\d*", text)
    numeros = [float(n) for n in numeros if float(n) >= 1000]  # filtra valores absurdos

    if len(numeros) >= 2:
        return min(numeros), max(numeros)
    elif len(numeros) == 1:
        return numeros[0], numeros[0]
    return None, None


# -------------------------------------------------------------------
# Classificação de senioridade
# -------------------------------------------------------------------

SENIORIDADE_KEYWORDS = {
    "Junior":    ["junior", "jr", "entry", "trainee", "intern", "associate", "estágio"],
    "Mid-Level": ["mid", "pleno", "mid-level", "intermediate", "ii"],
    "Senior":    ["senior", "sr", "sênior", "lead", "specialist", "iii"],
    "Staff":     ["staff", "principal", "architect", "manager", "director", "head", "vp", "chief"],
}


def classify_seniority(title: Optional[str], level: Optional[str] = None) -> str:
    """Infere senioridade a partir do título e do campo job_level."""
    if level and level not in ("Not Specified", ""):
        mapping = {
            "Associate":  "Junior",
            "Mid-Senior": "Senior",
            "Entry Level": "Junior",
            "Director":   "Staff",
            "Executive":  "Staff",
        }
        if level in mapping:
            return mapping[level]

    if not title:
        return "Not Specified"

    titulo_lower = title.lower()
    for nivel, keywords in SENIORIDADE_KEYWORDS.items():
        if any(kw in titulo_lower for kw in keywords):
            return nivel

    return "Mid-Level"  # default razoável


# -------------------------------------------------------------------
# Normalização de localização
# -------------------------------------------------------------------

def normalize_location(location: Optional[str], country: Optional[str] = None) -> dict:
    """Extrai país, região e modalidade de strings de localização."""
    modalidade = "Onsite"
    pais = safe_str(country) or "Unknown"
    regiao = safe_str(location) or "Unknown"

    loc_str = safe_str(location)
    if loc_str:
        loc_lower = loc_str.lower()
        if "remote" in loc_lower or "worldwide" in loc_lower:
            modalidade = "Remote"
        elif "hybrid" in loc_lower:
            modalidade = "Hybrid"

    return {"pais": pais, "regiao": regiao, "modalidade": modalidade}


# -------------------------------------------------------------------
# Normalização de modalidade
# -------------------------------------------------------------------

def normalize_job_type(job_type: Optional[str]) -> str:
    if not job_type:
        return "Onsite"
    mapping = {
        "full_time": "Onsite",
        "contract":  "Onsite",
        "remote":    "Remote",
        "hybrid":    "Hybrid",
        "onsite":    "Onsite",
    }
    return mapping.get(str(job_type).lower(), "Onsite")


# -------------------------------------------------------------------
# Extração de stacks do título
# -------------------------------------------------------------------

TECH_KEYWORDS = [
    "python", "sql", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "go", "scala", "r", "c++", "c#", "ruby", "php", "swift", "kotlin",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "airflow",
    "spark", "kafka", "hadoop", "dbt", "databricks", "snowflake", "bigquery",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "tensorflow", "pytorch", "scikit", "pandas", "numpy",
    "power bi", "tableau", "looker", "mlflow", "git", "linux",
]


def extract_stacks_from_title(title: Optional[str]) -> list:
    """Extrai tecnologias mencionadas no título da vaga usando word boundary."""
    if not title:
        return []
    titulo_lower = title.lower()
    found = []
    for kw in TECH_KEYWORDS:
        # Escapa caracteres especiais como "c++" e usa \b para word boundary
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, titulo_lower):
            found.append(kw)
    return found


# -------------------------------------------------------------------
# Transformação principal — API
# -------------------------------------------------------------------

def transform_api(df: pd.DataFrame, stacks_lookup: dict) -> pd.DataFrame:
    """Transforma DataFrame bruto da Remotive API."""
    if df.empty:
        log.warning("[transform] DataFrame da API está vazio.")
        return df

    registros = []
    skipped = 0

    for _, row in df.iterrows():
        titulo = safe_str(row.get("job_title"))
        if not titulo:
            skipped += 1
            continue

        # Salário
        sal_min, sal_max = parse_salary(row.get("salary_raw"))

        # Tags da API + stacks do título
        tags_api = str(row.get("tags", "")).split(", ")
        stacks_titulo = extract_stacks_from_title(titulo)
        todas_stacks = list(set([t.strip().lower() for t in tags_api if t.strip()] + stacks_titulo))

        # Localização
        loc = normalize_location(row.get("job_location"), country="Remote")

        # Enriquecimento com taxonomia
        for stack in todas_stacks or ["unknown"]:
            info = stacks_lookup.get(stack.lower(), {"categoria": "Outros", "area": "Outros"})
            registros.append({
                "job_title":     titulo,
                "company":       safe_str(row.get("company")) or "Unknown",
                "stack":         stack.title() if stack != "unknown" else "Unknown",
                "categoria":     info["categoria"],
                "area":          info["area"],
                "salario_min":   sal_min,
                "salario_max":   sal_max,
                "pais":          loc["pais"],
                "regiao":        loc["regiao"],
                "modalidade":    loc["modalidade"],
                "nivel":         classify_seniority(titulo),
                "data_publicacao": pd.to_datetime(row.get("first_seen"), errors="coerce"),
                "fonte":         "remotive_api",
            })

    result = pd.DataFrame(registros)
    log.info(f"[transform] API: {len(result)} registros transformados, {skipped} descartados.")
    return result


# -------------------------------------------------------------------
# Transformação principal — CSV
# -------------------------------------------------------------------

def transform_csv(df: pd.DataFrame, stacks_lookup: dict) -> pd.DataFrame:
    """Transforma DataFrame bruto do job_postings.csv."""
    if df.empty:
        log.warning("[transform] DataFrame do CSV está vazio.")
        return df

    # Remove duplicatas
    antes = len(df)
    df = df.drop_duplicates(subset=["job_title", "company"]).copy()
    log.info(f"[transform] CSV: {antes - len(df)} duplicatas removidas.")

    registros = []
    skipped = 0

    for _, row in df.iterrows():
        titulo = safe_str(row.get("job_title"))
        if not titulo:
            skipped += 1
            continue

        # Localização
        loc = normalize_location(
            row.get("job_location"),
            country=row.get("search_country")
        )
        # Sobrescreve modalidade com job_type do CSV
        job_type = safe_str(row.get("job_type"))
        if job_type:
            loc["modalidade"] = normalize_job_type(job_type)

        # Stacks inferidas do título
        stacks = extract_stacks_from_title(titulo) or ["unknown"]

        for stack in stacks:
            info = stacks_lookup.get(stack.lower(), {"categoria": "Outros", "area": "Outros"})
            registros.append({
                "job_title":     titulo,
                "company":       safe_str(row.get("company")) or "Unknown",
                "stack":         stack.title() if stack != "unknown" else "Unknown",
                "categoria":     info["categoria"],
                "area":          info["area"],
                "salario_min":   None,  # CSV não tem salário
                "salario_max":   None,
                "pais":          loc["pais"],
                "regiao":        loc["regiao"],
                "modalidade":    loc["modalidade"],
                "nivel":         classify_seniority(titulo, row.get("job_level")),
                "data_publicacao": pd.to_datetime(row.get("first_seen"), errors="coerce"),
                "fonte":         "csv_dataset",
            })

    result = pd.DataFrame(registros)
    log.info(f"[transform] CSV: {len(result)} registros transformados, {skipped} descartados.")
    return result


# -------------------------------------------------------------------
# Merge final
# -------------------------------------------------------------------

def transform_all(df_api: pd.DataFrame, df_csv: pd.DataFrame, df_json: pd.DataFrame) -> pd.DataFrame:
    """
    Integra e transforma todas as fontes.
    Retorna DataFrame unificado pronto para carga.
    """
    stacks_lookup = build_lookup(df_json)

    df_api_t = transform_api(df_api, stacks_lookup)
    df_csv_t = transform_csv(df_csv, stacks_lookup)

    combined = pd.concat([df_api_t, df_csv_t], ignore_index=True)

    # Garante tipos
    combined["data_publicacao"] = pd.to_datetime(combined["data_publicacao"], errors="coerce")
    combined["salario_min"]     = pd.to_numeric(combined["salario_min"], errors="coerce")
    combined["salario_max"]     = pd.to_numeric(combined["salario_max"], errors="coerce")

    log.info(f"[transform] Total combinado: {len(combined)} registros de {combined['fonte'].nunique()} fontes.")
    return combined


def run(df_api: pd.DataFrame, df_csv: pd.DataFrame, df_json: pd.DataFrame) -> pd.DataFrame:
    """Chamável pela DAG do Airflow."""
    return transform_all(df_api, df_csv, df_json)
