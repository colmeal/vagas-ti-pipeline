"""
metrics.py — Emite métricas finais do pipeline.
Gera contagens, logs e relatório JSON para o dashboard.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import psycopg2

from config import settings

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

QUERIES = {
    "total_vagas":         "SELECT COUNT(*) FROM fact_vagas",
    "total_empresas":      "SELECT COUNT(*) FROM dim_empresa",
    "total_tecnologias":   "SELECT COUNT(*) FROM dim_tecnologia",
    "total_localizacoes":  "SELECT COUNT(*) FROM dim_localizacao",
    "vagas_com_salario":   "SELECT COUNT(*) FROM fact_vagas WHERE salario_min IS NOT NULL",
    "vagas_remotas":       "SELECT COUNT(*) FROM fact_vagas fv JOIN dim_localizacao dl ON fv.localizacao_id = dl.localizacao_id WHERE dl.modalidade = 'Remote'",
    "top_stack": """
        SELECT dt.stack, COUNT(*) as total
        FROM fact_vagas fv
        JOIN dim_tecnologia dt ON fv.tecnologia_id = dt.tecnologia_id
        WHERE dt.stack != 'Unknown'
        GROUP BY dt.stack
        ORDER BY total DESC
        LIMIT 5
    """,
}


def emit_metrics() -> dict:
    """Executa queries analíticas e retorna dicionário de métricas."""
    conn = None
    metricas = {"gerado_em": datetime.utcnow().isoformat()}

    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )

        with conn.cursor() as cur:
            for nome, query in QUERIES.items():
                cur.execute(query)
                if nome == "top_stack":
                    rows = cur.fetchall()
                    metricas[nome] = [{"stack": r[0], "total": r[1]} for r in rows]
                else:
                    metricas[nome] = cur.fetchone()[0]

        # Log resumo
        log.info(
            f"[metrics] Pipeline concluído | "
            f"vagas={metricas.get('total_vagas')} | "
            f"empresas={metricas.get('total_empresas')} | "
            f"techs={metricas.get('total_tecnologias')} | "
            f"remotas={metricas.get('vagas_remotas')}"
        )

        # Persiste relatório em arquivo
        report_path = Path("/opt/airflow/logs/dq_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(metricas, f, indent=2, default=str)

        log.info(f"[metrics] Relatório salvo em {report_path}")

    except Exception as exc:
        log.error(f"[metrics] Erro ao emitir métricas: {exc}")
        metricas["erro"] = str(exc)
    finally:
        if conn:
            conn.close()

    return metricas


def run() -> dict:
    """Chamável pela DAG do Airflow."""
    return emit_metrics()
