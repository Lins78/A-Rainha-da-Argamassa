-- Schema PostgreSQL para o projeto A Rainha da Argamassa
-- Base de dados: revenda_argamassa

CREATE TABLE IF NOT EXISTS cliente (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS produto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    preco NUMERIC(12, 2) NOT NULL CHECK (preco >= 0),
    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0)
);

CREATE TABLE IF NOT EXISTS inventario (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL UNIQUE,
    estoque_atual INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    estoque_maximo INTEGER CHECK (estoque_maximo IS NULL OR estoque_maximo >= estoque_minimo),
    custo_medio NUMERIC(12, 2) CHECK (custo_medio IS NULL OR custo_medio >= 0),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_inventario_produto FOREIGN KEY (produto_id) REFERENCES produto(id)
);

CREATE TABLE IF NOT EXISTS pedido (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    total NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'efetivado', 'cancelado')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (cliente_id) REFERENCES cliente(id),
    CONSTRAINT fk_pedido_produto FOREIGN KEY (produto_id) REFERENCES produto(id)
);

CREATE TABLE IF NOT EXISTS formas_pagamento (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(40) NOT NULL UNIQUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

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
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    documento VARCHAR(20) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    email VARCHAR(120),
    endereco VARCHAR(255),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

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
);

CREATE TABLE IF NOT EXISTS vendas (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    forma_pagamento_id INTEGER NOT NULL,
    conta_bancaria_id INTEGER,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12, 2) NOT NULL CHECK (preco_unitario >= 0),
    total NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
    efetivada_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_venda_pedido FOREIGN KEY (pedido_id) REFERENCES pedido(id),
    CONSTRAINT fk_venda_cliente FOREIGN KEY (cliente_id) REFERENCES cliente(id),
    CONSTRAINT fk_venda_produto FOREIGN KEY (produto_id) REFERENCES produto(id),
    CONSTRAINT fk_venda_forma_pagamento FOREIGN KEY (forma_pagamento_id) REFERENCES formas_pagamento(id),
    CONSTRAINT fk_venda_conta_bancaria FOREIGN KEY (conta_bancaria_id) REFERENCES contas_bancarias(id)
);

CREATE TABLE IF NOT EXISTS estoque (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL,
    venda_id INTEGER NOT NULL UNIQUE,
    tipo VARCHAR(10) NOT NULL DEFAULT 'saida' CHECK (tipo = 'saida'),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    saldo_anterior INTEGER NOT NULL CHECK (saldo_anterior >= 0),
    saldo_atual INTEGER NOT NULL CHECK (saldo_atual >= 0),
    movimentado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_estoque_produto FOREIGN KEY (produto_id) REFERENCES produto(id),
    CONSTRAINT fk_estoque_venda FOREIGN KEY (venda_id) REFERENCES vendas(id)
);

CREATE TABLE IF NOT EXISTS relatorios (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('efetivada', 'cancelada')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    total NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
    criado_em TIMESTAMPTZ NOT NULL,
    efetivado_em TIMESTAMPTZ,
    cancelado_em TIMESTAMPTZ,
    motivo_cancelamento VARCHAR(200),
    CONSTRAINT fk_relatorio_pedido FOREIGN KEY (pedido_id) REFERENCES pedido(id),
    CONSTRAINT fk_relatorio_cliente FOREIGN KEY (cliente_id) REFERENCES cliente(id),
    CONSTRAINT fk_relatorio_produto FOREIGN KEY (produto_id) REFERENCES produto(id)
);

INSERT INTO formas_pagamento (nome, ativo)
SELECT * FROM (
    VALUES
        ('Dinheiro', TRUE),
        ('Pix', TRUE),
        ('Cartão de crédito', TRUE),
        ('Cartão de débito', TRUE),
        ('Boleto bancário', TRUE),
        ('Transferência bancária', TRUE)
) AS v(nome, ativo)
WHERE NOT EXISTS (
    SELECT 1 FROM formas_pagamento WHERE formas_pagamento.nome = v.nome
);

COMMENT ON TABLE cliente IS 'Clientes do sistema';
COMMENT ON TABLE produto IS 'Produtos disponíveis para venda';
COMMENT ON TABLE inventario IS 'Posição atual e parâmetros de controle do estoque';
COMMENT ON TABLE pedido IS 'Pedidos realizados pelos clientes';
COMMENT ON TABLE formas_pagamento IS 'Formas de pagamento disponíveis';
COMMENT ON TABLE contas_bancarias IS 'Contas bancárias de destino das vendas';
COMMENT ON TABLE entradas_estoque IS 'Entradas de produtos para alimentar o estoque';
COMMENT ON TABLE fornecedores IS 'Fornecedores de produtos e entradas de estoque';
COMMENT ON TABLE vendas IS 'Vendas efetivadas';
COMMENT ON TABLE estoque IS 'Movimentação de estoque por venda';
COMMENT ON TABLE relatorios IS 'Relatórios de pedidos efetivados e cancelados';
