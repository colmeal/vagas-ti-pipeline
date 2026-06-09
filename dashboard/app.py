"""
dashboard/app.py — Dashboard Streamlit para análise de vagas TI.
Conecta diretamente ao PostgreSQL e exibe visualizações analíticas.
"""
import os

import pandas as pd
import streamlit as st
import psycopg2
import plotly.express as px

# -------------------------------------------------------------------
# Configuração da página
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Mercado de Vagas TI",
    page_icon="💼",
    layout="wide",
)

# -------------------------------------------------------------------
# Conexão com o banco
# -------------------------------------------------------------------

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "vagas_db"),
        user=os.getenv("DB_USER", "vagas_user"),
        password=os.getenv("DB_PASSWORD", "vagas_pass"),
    )


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
st.title("💼 Mercado de Vagas em Tecnologia")
st.caption("Pipeline de Data Integration · ESPM 2026.1")
st.divider()

# -------------------------------------------------------------------
# KPIs
# -------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_vagas    = query("SELECT COUNT(*) AS n FROM fact_vagas").iloc[0]["n"]
total_empresas = query("SELECT COUNT(*) AS n FROM dim_empresa").iloc[0]["n"]
total_techs    = query("SELECT COUNT(*) AS n FROM dim_tecnologia WHERE stack != 'Unknown'").iloc[0]["n"]
vagas_remotas  = query("""
    SELECT COUNT(*) AS n FROM fact_vagas fv
    JOIN dim_localizacao dl ON fv.localizacao_id = dl.localizacao_id
    WHERE dl.modalidade = 'Remote'
""").iloc[0]["n"]

col1.metric("Total de Vagas",    f"{total_vagas:,}")
col2.metric("Empresas",          f"{total_empresas:,}")
col3.metric("Tecnologias",       f"{total_techs:,}")
col4.metric("Vagas Remotas",     f"{vagas_remotas:,}")

st.divider()

# -------------------------------------------------------------------
# Linha 1: Top Stacks + Distribuição por Modalidade
# -------------------------------------------------------------------
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("🏆 Top 15 Tecnologias Mais Exigidas")
    df_stacks = query("""
        SELECT dt.stack, dt.categoria, dt.area, COUNT(*) AS total
        FROM fact_vagas fv
        JOIN dim_tecnologia dt ON fv.tecnologia_id = dt.tecnologia_id
        WHERE dt.stack != 'Unknown'
        GROUP BY dt.stack, dt.categoria, dt.area
        ORDER BY total DESC
        LIMIT 15
    """)
    if not df_stacks.empty:
        fig = px.bar(
            df_stacks, x="total", y="stack", orientation="h",
            color="categoria", title="",
            labels={"total": "Nº de Vagas", "stack": "Tecnologia"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=420)
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("🌍 Modalidade de Trabalho")
    df_modal = query("""
        SELECT dl.modalidade, COUNT(*) AS total
        FROM fact_vagas fv
        JOIN dim_localizacao dl ON fv.localizacao_id = dl.localizacao_id
        GROUP BY dl.modalidade
    """)
    if not df_modal.empty:
        fig2 = px.pie(df_modal, names="modalidade", values="total", hole=0.4)
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# -------------------------------------------------------------------
# Linha 2: Evolução temporal + Senioridade
# -------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.subheader("📈 Evolução de Vagas por Mês")
    df_tempo = query("""
        SELECT dt.ano, dt.mes, COUNT(*) AS total
        FROM fact_vagas fv
        JOIN dim_tempo dt ON fv.tempo_id = dt.tempo_id
        GROUP BY dt.ano, dt.mes
        ORDER BY dt.ano, dt.mes
    """)
    if not df_tempo.empty:
        df_tempo["periodo"] = df_tempo["ano"].astype(str) + "-" + df_tempo["mes"].astype(str).str.zfill(2)
        fig3 = px.line(df_tempo, x="periodo", y="total", markers=True,
                       labels={"periodo": "Mês", "total": "Vagas"})
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("👤 Distribuição por Senioridade")
    df_nivel = query("""
        SELECT nivel, COUNT(*) AS total
        FROM fact_vagas
        WHERE nivel IS NOT NULL AND nivel != 'Not Specified'
        GROUP BY nivel
        ORDER BY total DESC
    """)
    if not df_nivel.empty:
        fig4 = px.bar(df_nivel, x="nivel", y="total", color="nivel",
                      labels={"nivel": "Nível", "total": "Vagas"})
        fig4.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# -------------------------------------------------------------------
# Linha 3: Top Empresas + Salários
# -------------------------------------------------------------------
c5, c6 = st.columns(2)

with c5:
    st.subheader("🏢 Empresas com Mais Vagas")
    df_emp = query("""
        SELECT de.nome_empresa, COUNT(*) AS total
        FROM fact_vagas fv
        JOIN dim_empresa de ON fv.empresa_id = de.empresa_id
        GROUP BY de.nome_empresa
        ORDER BY total DESC
        LIMIT 12
    """)
    if not df_emp.empty:
        fig5 = px.bar(df_emp, x="total", y="nome_empresa", orientation="h",
                      labels={"total": "Vagas", "nome_empresa": "Empresa"})
        fig5.update_layout(yaxis=dict(autorange="reversed"), height=380)
        st.plotly_chart(fig5, use_container_width=True)

with c6:
    st.subheader("💰 Salário Médio por Categoria")
    df_sal = query("""
        SELECT dt.categoria,
               ROUND(AVG(fv.salario_min)::numeric, 0) AS media_min,
               ROUND(AVG(fv.salario_max)::numeric, 0) AS media_max
        FROM fact_vagas fv
        JOIN dim_tecnologia dt ON fv.tecnologia_id = dt.tecnologia_id
        WHERE fv.salario_min IS NOT NULL
          AND dt.categoria != 'Outros'
        GROUP BY dt.categoria
        ORDER BY media_min DESC
    """)
    if not df_sal.empty:
        fig6 = px.bar(df_sal, x="categoria", y=["media_min", "media_max"],
                      barmode="group",
                      labels={"value": "USD/ano", "categoria": "Categoria"},
                      color_discrete_sequence=["#636EFA", "#EF553B"])
        fig6.update_layout(height=380)
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("Dados de salário disponíveis apenas nas vagas da Remotive API.")

st.divider()

# -------------------------------------------------------------------
# Tabela detalhada com filtros
# -------------------------------------------------------------------
st.subheader("🔍 Explorar Vagas")

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    paises = ["Todos"] + query(
        "SELECT DISTINCT pais FROM dim_localizacao ORDER BY pais"
    )["pais"].tolist()
    filtro_pais = st.selectbox("País", paises)

with col_f2:
    niveis = ["Todos", "Junior", "Mid-Level", "Senior", "Staff"]
    filtro_nivel = st.selectbox("Senioridade", niveis)

with col_f3:
    modalidades = ["Todos", "Remote", "Hybrid", "Onsite"]
    filtro_modal = st.selectbox("Modalidade", modalidades)

sql_filtro = """
    SELECT fv.titulo, de.nome_empresa, dl.pais, dl.modalidade,
           fv.nivel, dt.stack, fv.salario_min, fv.salario_max, fv.fonte
    FROM fact_vagas fv
    JOIN dim_empresa     de ON fv.empresa_id     = de.empresa_id
    JOIN dim_localizacao dl ON fv.localizacao_id = dl.localizacao_id
    JOIN dim_tecnologia  dt ON fv.tecnologia_id  = dt.tecnologia_id
    WHERE 1=1
"""
params = []

if filtro_pais != "Todos":
    sql_filtro += f" AND dl.pais = '{filtro_pais}'"
if filtro_nivel != "Todos":
    sql_filtro += f" AND fv.nivel = '{filtro_nivel}'"
if filtro_modal != "Todos":
    sql_filtro += f" AND dl.modalidade = '{filtro_modal}'"

sql_filtro += " LIMIT 200"

df_tabela = query(sql_filtro)
st.dataframe(df_tabela, use_container_width=True, height=320)
st.caption(f"{len(df_tabela)} vagas exibidas (máx. 200).")
