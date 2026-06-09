"""
load.py — Carga dimensional no PostgreSQL.
psycopg2 + execute_batch + upsert com ON CONFLICT.
"""
import logging
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

from config import settings

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )


def get_or_create_empresa(cursor, nome_empresa: str) -> int:
    cursor.execute(
        """
        INSERT INTO dim_empresa (nome_empresa)
        VALUES (%s)
        ON CONFLICT (nome_empresa) DO UPDATE SET nome_empresa = EXCLUDED.nome_empresa
        RETURNING empresa_id
        """,
        (nome_empresa[:255],),
    )
    return cursor.fetchone()[0]


def get_or_create_tecnologia(cursor, stack: str, categoria: str, area: str) -> int:
    cursor.execute(
        """
        INSERT INTO dim_tecnologia (stack, categoria, area)
        VALUES (%s, %s, %s)
        ON CONFLICT (stack) DO UPDATE SET categoria = EXCLUDED.categoria, area = EXCLUDED.area
        RETURNING tecnologia_id
        """,
        (stack[:100], categoria[:100], area[:100]),
    )
    return cursor.fetchone()[0]


def get_or_create_localizacao(cursor, pais: str, regiao: str, modalidade: str) -> int:
    cursor.execute(
        """
        INSERT INTO dim_localizacao (pais, regiao, modalidade)
        VALUES (%s, %s, %s)
        ON CONFLICT (pais, regiao, modalidade) DO UPDATE SET pais = EXCLUDED.pais
        RETURNING localizacao_id
        """,
        (pais[:100], regiao[:150], modalidade[:50]),
    )
    return cursor.fetchone()[0]


def get_or_create_tempo(cursor, data) -> Optional[int]:
    if data is None or (isinstance(data, float) and pd.isna(data)):
        return None
    try:
        d = pd.Timestamp(data)
        if pd.isna(d):
            return None
    except Exception:
        return None

    cursor.execute(
        """
        INSERT INTO dim_tempo (data, semana, mes, ano)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (data) DO NOTHING
        RETURNING tempo_id
        """,
        (d.date(), int(d.isocalendar()[1]), int(d.month), int(d.year)),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("SELECT tempo_id FROM dim_tempo WHERE data = %s", (d.date(),))
    row = cursor.fetchone()
    return row[0] if row else None


def load_data(df: pd.DataFrame) -> dict:
    if df.empty:
        log.warning("[load] DataFrame vazio. Nenhum dado carregado.")
        return {"fact_vagas": 0}

    log.info(f"[load] Iniciando carga de {len(df)} registros...")

    conn = None
    total_fato = 0
    erros = 0

    try:
        conn = get_connection()
        cur = conn.cursor()

        for i, row in df.iterrows():
            try:
                empresa   = str(row.get("company") or "Unknown")[:255]
                stack     = str(row.get("stack") or "Unknown")[:100]
                categoria = str(row.get("categoria") or "Outros")[:100]
                area      = str(row.get("area") or "Outros")[:100]
                pais      = str(row.get("pais") or "Unknown")[:100]
                regiao    = str(row.get("regiao") or "Unknown")[:150]
                modalidade = str(row.get("modalidade") or "Onsite")[:50]
                titulo    = str(row.get("job_title") or "")[:255]
                nivel     = str(row.get("nivel") or "")[:50]
                fonte     = str(row.get("fonte") or "")[:50]

                sal_min = row.get("salario_min")
                sal_max = row.get("salario_max")
                sal_min = None if (sal_min is None or (isinstance(sal_min, float) and pd.isna(sal_min))) else float(sal_min)
                sal_max = None if (sal_max is None or (isinstance(sal_max, float) and pd.isna(sal_max))) else float(sal_max)

                empresa_id    = get_or_create_empresa(cur, empresa)
                tecnologia_id = get_or_create_tecnologia(cur, stack, categoria, area)
                localizacao_id = get_or_create_localizacao(cur, pais, regiao, modalidade)
                tempo_id      = get_or_create_tempo(cur, row.get("data_publicacao"))

                data_pub = None
                try:
                    ts = pd.Timestamp(row.get("data_publicacao"))
                    if not pd.isna(ts):
                        data_pub = ts.date()
                except Exception:
                    pass

                cur.execute(
                    """
                    INSERT INTO fact_vagas (
                        titulo, salario_min, salario_max, data_publicacao,
                        nivel, fonte,
                        empresa_id, tecnologia_id, localizacao_id, tempo_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (titulo, sal_min, sal_max, data_pub, nivel, fonte,
                     empresa_id, tecnologia_id, localizacao_id, tempo_id),
                )
                total_fato += 1

                # Commit a cada 500 registros
                if total_fato % 500 == 0:
                    conn.commit()
                    log.info(f"[load] {total_fato} registros carregados...")

            except Exception as e:
                erros += 1
                conn.rollback()
                if erros <= 3:
                    log.warning(f"[load] Erro no registro {i}: {e}")
                # Reconecta cursor após rollback
                cur = conn.cursor()
                continue

        conn.commit()
        log.info(f"[load] Concluido: {total_fato} inseridos, {erros} erros.")

    except Exception as exc:
        if conn:
            conn.rollback()
        raise RuntimeError(f"[load] Erro critico: {exc}") from exc
    finally:
        if conn:
            conn.close()

    return {"fact_vagas": total_fato, "erros": erros}


def run(df: pd.DataFrame) -> dict:
    return load_data(df)