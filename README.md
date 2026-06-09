# 💼 Pipeline de Análise do Mercado de Vagas em TI

> Disciplina: Data Integration · ESPM 2026.1

Pipeline ETL end-to-end que integra múltiplas fontes de dados sobre vagas em tecnologia para identificar tendências de mercado, tecnologias mais demandadas, faixas salariais e perfil das contratações.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Fontes de Dados](#fontes-de-dados)
- [Pré-requisitos](#pré-requisitos)
- [Como Executar](#como-executar)
- [Estrutura do Repositório](#estrutura-do-repositório)
- [Modelagem Dimensional](#modelagem-dimensional)
- [Dashboard](#dashboard)
- [Consultas Analíticas](#consultas-analíticas)
- [Testes](#testes)
- [Equipe](#equipe)

---

## 👁️ Visão Geral

O projeto coleta vagas de TI de três fontes distintas, valida e transforma os dados, carrega em um banco PostgreSQL com modelagem dimensional e exibe os resultados em um dashboard interativo com Streamlit.

**Resultados obtidos** (crescem a cada execução do pipeline):
- 40.000+ vagas processadas
- 3.962+ empresas mapeadas
- 137 tecnologias identificadas
- Dados de salário, senioridade, modalidade e localização

---

## 🏗️ Arquitetura

```
┌───────────────────────────────────────────────────────────────┐
│                      FONTES DE DADOS                          │
│  Remotive API (JSON)  ·  job_postings.csv  ·  stacks_map.json │
└───────────────┬───────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                     APACHE AIRFLOW DAG                      │
│  extract_api → extract_csv → extract_json                   │
│       → validate_quality → transform_data                   │
│       → load_postgres → emit_metrics → notify_done          │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                   POSTGRESQL (Dimensional)                  │
│  fact_vagas · dim_empresa · dim_tecnologia                  │
│  dim_localizacao · dim_tempo                                │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                   DASHBOARD STREAMLIT                       │
│  KPIs · Gráficos · Filtros · Tabela explorável              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Fontes de Dados

| Fonte | Tipo | Descrição |
|-------|------|-----------|
| [Remotive API](https://remotive.com/api-documentation) | REST/JSON | Vagas remotas em tempo real com tags de tecnologia |
| `job_postings.csv` | CSV | ~12.200 vagas reais de TI (LinkedIn) com empresa, localização e senioridade |
| `stacks_map.json` | JSON | Taxonomia de 50+ tecnologias mapeadas para categorias e áreas |

---

## ✅ Pré-requisitos

Instale apenas o **Docker Desktop** — ele cuida de tudo o mais (Airflow, PostgreSQL, Python, dependências).

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac/Linux)
- Windows 10/11: requer **WSL2** habilitado (o próprio Docker Desktop orienta a instalação)

> **Não é necessário** instalar Python, Airflow, PostgreSQL ou qualquer outra dependência manualmente.

---

## 🚀 Como Executar

### 1. Clone ou extraia o projeto

```bash
git clone https://github.com/seu-usuario/vagas-ti-pipeline.git
cd vagas-ti-pipeline
```

Ou extraia o `.zip` e entre na pasta do projeto.

### 2. Abra o Docker Desktop

Aguarde aparecer **"Engine running"** na barra inferior.

### 3. Suba o ambiente

No terminal, dentro da pasta do projeto:

```bash
docker compose up --build
```

> Na primeira execução pode demorar **10–15 minutos** pois baixa as imagens do Docker (~1.5 GB). Nas próximas é muito mais rápido.

### 4. Acesse os serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Airflow UI | http://localhost:8080 | admin / admin |
| Dashboard | http://localhost:8501 | — |
| PostgreSQL | localhost:5433 | vagas_user / vagas_pass |

> **PostgreSQL** — acesso direto ao banco de dados para rodar queries SQL e explorar as tabelas geradas pelo pipeline. Para acessar via terminal (sem instalar ferramentas externas):
> ```bash
> docker exec -it vagas_postgres_dados psql -U vagas_user -d vagas_db
> ```
> Para sair: `\q`

### 5. Dispare o pipeline

1. Acesse http://localhost:8080
2. Localize a DAG **`vagas_pipeline`**
3. Clique em ▶️ **Trigger DAG**
4. Acompanhe as 8 tasks em tempo real

### 6. Visualize o dashboard

Acesse http://localhost:8501 após o pipeline concluir.

### 7. Para encerrar

```bash
Ctrl + C
```

---

## 📁 Estrutura do Repositório

```
/
├── dags/
│   └── vagas_pipeline.py        ← DAG do Airflow (8 tasks)
├── etl/
│   ├── config.py                ← Configurações centralizadas
│   ├── extract_api.py           ← Extração Remotive API
│   ├── extract_csv.py           ← Extração job_postings.csv
│   ├── extract_json.py          ← Extração stacks_map.json
│   ├── validate.py              ← Validações de qualidade
│   ├── transform.py             ← Transformações ETL
│   ├── load.py                  ← Carga no PostgreSQL
│   └── metrics.py               ← Métricas do pipeline
├── sql/
│   └── schema.sql               ← Modelagem dimensional
├── data/
│   ├── job_postings.csv         ← Dataset principal (~12k vagas)
│   └── stacks_map.json          ← Taxonomia de tecnologias
├── dashboard/
│   └── app.py                   ← Dashboard Streamlit
├── tests/
│   └── test_transform.py        ← Testes unitários (pytest)
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.dashboard
├── requirements.txt
└── .env.example
```

---

## 🗄️ Modelagem Dimensional

```
fact_vagas
├── empresa_id      → dim_empresa     (nome, setor)
├── tecnologia_id   → dim_tecnologia  (stack, categoria, área)
├── localizacao_id  → dim_localizacao (país, região, modalidade)
└── tempo_id        → dim_tempo       (data, semana, mês, ano)
```

---

## 📈 Dashboard

O dashboard Streamlit exibe:

- **KPIs**: total de vagas, empresas, tecnologias e vagas remotas
- **Top 15 tecnologias** mais exigidas por categoria
- **Modalidade de trabalho**: presencial, remoto, híbrido
- **Evolução de vagas** por mês
- **Distribuição por senioridade**: Senior, Mid-Level, Junior, Staff
- **Top empresas** com mais vagas
- **Salário médio** mínimo e máximo por categoria
- **Tabela explorável** com filtros por país, senioridade e modalidade

### Screenshots

**🏆 Top 15 Tecnologias Mais Exigidas**

![🏆 Top 15 Tecnologias Mais Exigidas](assets/🏆%20Top%2015%20Tecnologias%20Mais%20Exigidas.png)

**🌍 Modalidade de Trabalho**

![🌍 Modalidade de Trabalho](assets/🌍%20Modalidade%20de%20Trabalho.png)

**📈 Evolução de Vagas por Mês**

![📈 Evolução de Vagas por Mês](assets/📈%20Evolução%20de%20Vagas%20por%20Mês.png)

**👤 Distribuição por Senioridade**

![👤 Distribuição por Senioridade](assets/👤%20Distribuição%20por%20Senioridade.png)

**🏢 Empresas com Mais Vagas**

![🏢 Empresas com Mais Vagas](assets/🏢%20Empresas%20com%20Mais%20Vagas.png)

**💰 Salário Médio por Categoria**

![💰 Salário Médio por Categoria](assets/💰%20Salário%20Médio%20por%20Categoria.png)

---

## 🔍 Consultas Analíticas

As queries abaixo podem ser executadas diretamente no banco via terminal, sem precisar instalar ferramentas externas:

```bash
docker exec -it vagas_postgres_dados psql -U vagas_user -d vagas_db
```

> Para sair do terminal do banco: `\q`

### Resultados obtidos

**Top 10 tecnologias mais exigidas** (resultado real do pipeline):

| # | Stack | Vagas |
|---|-------|-------|
| 1 | SQL | 448 |
| 2 | AWS | 348 |
| 3 | Azure | 344 |
| 4 | Python | 260 |
| 5 | AI/ML | 192 |
| 6 | REST | 168 |
| 7 | Databricks | 164 |
| 8 | React | 156 |
| 9 | Java | 156 |
| 10 | Github | 144 |

> SQL, AWS e Azure lideram — o mercado está fortemente focado em **cloud e dados**.

```sql
-- 1. Top 10 stacks mais exigidas
SELECT dt.stack, COUNT(*) AS total
FROM fact_vagas fv
JOIN dim_tecnologia dt ON fv.tecnologia_id = dt.tecnologia_id
WHERE dt.stack != 'Unknown'
GROUP BY dt.stack ORDER BY total DESC LIMIT 10;

-- 2. Salário médio por categoria de tecnologia
SELECT dt.categoria,
       ROUND(AVG(fv.salario_min), 0) AS media_min,
       ROUND(AVG(fv.salario_max), 0) AS media_max
FROM fact_vagas fv
JOIN dim_tecnologia dt ON fv.tecnologia_id = dt.tecnologia_id
WHERE fv.salario_min IS NOT NULL
GROUP BY dt.categoria ORDER BY media_min DESC;

-- 3. Volume de vagas por mês
SELECT dt.ano, dt.mes, COUNT(*) AS total
FROM fact_vagas fv
JOIN dim_tempo dt ON fv.tempo_id = dt.tempo_id
GROUP BY dt.ano, dt.mes ORDER BY dt.ano, dt.mes;

-- 4. Distribuição remoto/híbrido/presencial
SELECT dl.modalidade, COUNT(*) AS total
FROM fact_vagas fv
JOIN dim_localizacao dl ON fv.localizacao_id = dl.localizacao_id
GROUP BY dl.modalidade;

-- 5. Top empresas por número de vagas
SELECT de.nome_empresa, COUNT(*) AS total
FROM fact_vagas fv
JOIN dim_empresa de ON fv.empresa_id = de.empresa_id
GROUP BY de.nome_empresa ORDER BY total DESC LIMIT 10;
```

---

## 🧪 Testes

```bash
docker compose exec airflow pytest /opt/airflow/tests/test_transform.py -v
```

---