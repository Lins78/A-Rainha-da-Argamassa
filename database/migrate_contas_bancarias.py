"""Migra o banco existente para registrar o destino bancario das vendas."""

import os

import psycopg2
from sqlalchemy.engine import make_url


DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Defina DATABASE_URL com a conexao PostgreSQL.")

url = make_url(DATABASE_URL)
connection = psycopg2.connect(
    host=url.host,
    port=url.port,
    user=url.username,
    password=url.password,
    dbname=url.database,
)
connection.autocommit = True

with connection.cursor() as cursor:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contas_bancarias (
            id SERIAL PRIMARY KEY,
            banco VARCHAR(100) NOT NULL,
            agencia VARCHAR(20) NOT NULL,
            numero VARCHAR(30) NOT NULL,
            tipo_conta VARCHAR(20) NOT NULL DEFAULT 'corrente'
                CHECK (tipo_conta IN ('corrente', 'poupanca', 'pagamento')),
            titular VARCHAR(100) NOT NULL,
            documento VARCHAR(20),
            chave_pix VARCHAR(100),
            ativa BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT uq_conta_bancaria_identificacao UNIQUE (banco, agencia, numero)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fornecedores (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            documento VARCHAR(20) NOT NULL UNIQUE,
            telefone VARCHAR(20),
            email VARCHAR(120),
            endereco VARCHAR(255),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario (
            id SERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL UNIQUE,
            estoque_atual INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
            estoque_minimo INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
            estoque_maximo INTEGER CHECK (estoque_maximo IS NULL OR estoque_maximo >= estoque_minimo),
            custo_medio NUMERIC(12, 2) CHECK (custo_medio IS NULL OR custo_medio >= 0),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_inventario_produto FOREIGN KEY (produto_id) REFERENCES produto(id)
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO inventario (produto_id, estoque_atual)
        SELECT id, estoque FROM produto p
        WHERE NOT EXISTS (
            SELECT 1 FROM inventario i WHERE i.produto_id = p.id
        )
        """
    )
    cursor.execute(
        """
        UPDATE inventario i
        SET custo_medio = historico.custo_medio
        FROM (
            SELECT produto_id,
                   ROUND(SUM(custo_unitario * quantidade) / NULLIF(SUM(quantidade), 0), 2)
                       AS custo_medio
            FROM entradas_estoque
            GROUP BY produto_id
        ) AS historico
        WHERE i.produto_id = historico.produto_id
        """
    )
    cursor.execute("ALTER TABLE inventario ALTER COLUMN custo_medio DROP NOT NULL")
    cursor.execute("ALTER TABLE inventario ALTER COLUMN custo_medio DROP DEFAULT")
    cursor.execute(
        """
        UPDATE inventario i
        SET custo_medio = NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM entradas_estoque e WHERE e.produto_id = i.produto_id
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS entradas_estoque (
            id SERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER,
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            custo_unitario NUMERIC(12, 2) NOT NULL CHECK (custo_unitario >= 0),
            origem VARCHAR(100),
            documento VARCHAR(50),
            observacao VARCHAR(255),
            saldo_anterior INTEGER NOT NULL CHECK (saldo_anterior >= 0),
            saldo_atual INTEGER NOT NULL CHECK (saldo_atual > saldo_anterior),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_entrada_produto FOREIGN KEY (produto_id) REFERENCES produto(id),
            CONSTRAINT fk_entrada_fornecedor FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id)
        )
        """
    )
    cursor.execute("ALTER TABLE entradas_estoque ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER")
    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_entrada_fornecedor'
            ) THEN
                ALTER TABLE entradas_estoque
                ADD CONSTRAINT fk_entrada_fornecedor
                FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
            END IF;
        END $$;
        """
    )
    cursor.execute("ALTER TABLE vendas ADD COLUMN IF NOT EXISTS conta_bancaria_id INTEGER")
    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_venda_conta_bancaria'
            ) THEN
                ALTER TABLE vendas
                ADD CONSTRAINT fk_venda_conta_bancaria
                FOREIGN KEY (conta_bancaria_id) REFERENCES contas_bancarias(id);
            END IF;
        END $$;
        """
    )

connection.close()
print("MIGRATION_OK")
