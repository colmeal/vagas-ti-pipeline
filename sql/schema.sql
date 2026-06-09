-- =============================================================
-- Pipeline de Vagas TI — Schema Dimensional
-- Disciplina: Data Integration · ESPM 2026.1
-- =============================================================

-- Dimensão Empresa
CREATE TABLE IF NOT EXISTS dim_empresa (
    empresa_id   SERIAL PRIMARY KEY,
    nome_empresa VARCHAR(255) NOT NULL UNIQUE,
    setor        VARCHAR(100)
);

-- Dimensão Tecnologia
CREATE TABLE IF NOT EXISTS dim_tecnologia (
    tecnologia_id SERIAL PRIMARY KEY,
    stack         VARCHAR(100) NOT NULL UNIQUE,
    categoria     VARCHAR(100),
    area          VARCHAR(100)
);

-- Dimensão Localização
CREATE TABLE IF NOT EXISTS dim_localizacao (
    localizacao_id SERIAL PRIMARY KEY,
    pais           VARCHAR(100),
    regiao         VARCHAR(150),
    modalidade     VARCHAR(50),
    UNIQUE (pais, regiao, modalidade)
);

-- Dimensão Tempo
CREATE TABLE IF NOT EXISTS dim_tempo (
    tempo_id SERIAL PRIMARY KEY,
    data     DATE NOT NULL UNIQUE,
    semana   INT,
    mes      INT,
    ano      INT
);

-- Tabela Fato Vagas
CREATE TABLE IF NOT EXISTS fact_vagas (
    id_vaga        SERIAL PRIMARY KEY,
    titulo         VARCHAR(255),
    salario_min    NUMERIC(12, 2),
    salario_max    NUMERIC(12, 2),
    data_publicacao DATE,
    nivel          VARCHAR(50),
    fonte          VARCHAR(50),
    empresa_id     INT REFERENCES dim_empresa(empresa_id),
    tecnologia_id  INT REFERENCES dim_tecnologia(tecnologia_id),
    localizacao_id INT REFERENCES dim_localizacao(localizacao_id),
    tempo_id       INT REFERENCES dim_tempo(tempo_id),
    criado_em      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices analíticos
CREATE INDEX IF NOT EXISTS idx_fact_empresa      ON fact_vagas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fact_tecnologia   ON fact_vagas(tecnologia_id);
CREATE INDEX IF NOT EXISTS idx_fact_localizacao  ON fact_vagas(localizacao_id);
CREATE INDEX IF NOT EXISTS idx_fact_tempo        ON fact_vagas(tempo_id);
CREATE INDEX IF NOT EXISTS idx_fact_data         ON fact_vagas(data_publicacao);
