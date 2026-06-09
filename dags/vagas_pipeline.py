"""
DAG: vagas_pipeline
===================
Pipeline ETL — Análise de Vagas TI 
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
sys.path.append("/opt/airflow/etl")

log = logging.getLogger(__name__)

# Usa /opt/airflow/data que é volume montado — persiste entre tasks
TMP_DIR   = "/opt/airflow/data/tmp"
TMP_API   = f"{TMP_DIR}/df_api.json"
TMP_CSV   = f"{TMP_DIR}/df_csv.json"
TMP_JSON  = f"{TMP_DIR}/df_json.json"
TMP_FINAL = f"{TMP_DIR}/df_final.json"

DEFAULT_ARGS = {
    "owner": "espm-data-integration",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
}

def _ensure_tmp():
    import os
    os.makedirs(TMP_DIR, exist_ok=True)

def task_extract_api(**context):
    _ensure_tmp()
    import extract_api as mod
    df = mod.run()
    df.to_json(TMP_API, orient="records", date_format="iso")
    log.info(f"[DAG] extract_api: {len(df)} registros -> {TMP_API}")

def task_extract_csv(**context):
    _ensure_tmp()
    import extract_csv as mod
    df = mod.run()
    df.to_json(TMP_CSV, orient="records", date_format="iso")
    log.info(f"[DAG] extract_csv: {len(df)} registros -> {TMP_CSV}")

def task_extract_json(**context):
    _ensure_tmp()
    import extract_json as mod
    df = mod.run()
    df.to_json(TMP_JSON, orient="records")
    log.info(f"[DAG] extract_json: {len(df)} tecnologias -> {TMP_JSON}")

def task_validate_quality(**context):
    import pandas as pd, validate as mod
    df_api = pd.read_json(TMP_API)
    df_csv = pd.read_json(TMP_CSV)
    rel = mod.run(df_api, df_csv)
    log.info(f"[DAG] validate: DQ API={rel['api']['dq_score']} | CSV={rel['csv']['dq_score']}")

def task_transform_data(**context):
    import pandas as pd, transform as mod
    df_api  = pd.read_json(TMP_API)
    df_csv  = pd.read_json(TMP_CSV)
    df_json = pd.read_json(TMP_JSON)
    df_final = mod.run(df_api, df_csv, df_json)
    df_final.to_json(TMP_FINAL, orient="records", date_format="iso")
    log.info(f"[DAG] transform_data: {len(df_final)} registros -> {TMP_FINAL}")

def task_load_postgres(**context):
    import pandas as pd, load as mod
    df = pd.read_json(TMP_FINAL)
    log.info(f"[DAG] load_postgres: carregando {len(df)} registros...")
    resultado = mod.run(df)
    log.info(f"[DAG] load_postgres resultado: {resultado}")

def task_emit_metrics(**context):
    import metrics as mod
    resultado = mod.run()
    log.info(f"[DAG] emit_metrics: {resultado}")

def task_notify_done(**context):
    import os
    log.info("=" * 60)
    log.info("[DAG] Pipeline vagas_pipeline concluido com sucesso!")
    # Limpa arquivos temporários
    for f in [TMP_API, TMP_CSV, TMP_JSON, TMP_FINAL]:
        try:
            os.remove(f)
        except:
            pass
    log.info("=" * 60)

with DAG(
    dag_id="vagas_pipeline",
    description="Pipeline ETL — Análise de Vagas TI | ESPM 2026.1",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["espm", "vagas", "etl", "data-integration"],
) as dag:

    t_extract_api  = PythonOperator(task_id="extract_api",      python_callable=task_extract_api)
    t_extract_csv  = PythonOperator(task_id="extract_csv",      python_callable=task_extract_csv)
    t_extract_json = PythonOperator(task_id="extract_json",     python_callable=task_extract_json)
    t_validate     = PythonOperator(task_id="validate_quality", python_callable=task_validate_quality)
    t_transform    = PythonOperator(task_id="transform_data",   python_callable=task_transform_data)
    t_load         = PythonOperator(task_id="load_postgres",    python_callable=task_load_postgres)
    t_metrics      = PythonOperator(task_id="emit_metrics",     python_callable=task_emit_metrics)
    t_notify       = PythonOperator(task_id="notify_done",      python_callable=task_notify_done)

    [t_extract_api, t_extract_csv, t_extract_json] >> t_validate
    t_validate >> t_transform >> t_load >> t_metrics >> t_notify