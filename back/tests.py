import os
import tempfile

import pytest
from flask import Flask

try:
    from back.app import create_app
    from back.config import Config
    from back.models import (
        db, Produto, Cliente, Pedido, Venda, FormaPagamento, ContaBancaria,
        EntradaEstoque, Fornecedor, Inventario,
        MovimentacaoEstoque,
    )
    from back.services import (
        soma, subtracao, multiplicacao, divisao,
        calcular_desconto, calcular_margem_lucro, calcular_media_precos
    )
except ImportError:  # pragma: no cover
    from app import create_app
    from config import Config
    from models import (
        db, Produto, Cliente, Pedido, Venda, FormaPagamento, ContaBancaria,
        EntradaEstoque, Fornecedor, Inventario,
        MovimentacaoEstoque,
    )
    from services import (
        soma, subtracao, multiplicacao, divisao,
        calcular_desconto, calcular_margem_lucro, calcular_media_precos
    )


@pytest.fixture
def app_client():
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        db.session.add(FormaPagamento(nome="Pix"))
        db.session.add(ContaBancaria(
            banco="Banco de Teste",
            agencia="0001",
            numero="12345",
            tipo_conta="corrente",
            titular="Titular de Teste",
        ))
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_soma():
    assert soma([1, 2, 3]) == 6


def test_subtracao():
    assert subtracao(10, 4) == 6


def test_multiplicacao():
    assert multiplicacao(2, 3) == 6


def test_divisao_valida():
    resultado, erro = divisao(10, 2)
    assert resultado == 5
    assert erro is None


def test_divisao_por_zero():
    resultado, erro = divisao(10, 0)
    assert resultado is None
    assert erro == "Erro: divisão por zero não é permitida."


def test_calcular_desconto():
    desconto, preco_final = calcular_desconto(100, 10)
    assert desconto == 10
    assert preco_final == 90


def test_calcular_margem_lucro():
    margem_valor, preco_venda = calcular_margem_lucro(50, 30)
    assert margem_valor == 15
    assert preco_venda == 65


def test_calcular_media_precos_sem_produtos(app_client):
    media, erro = calcular_media_precos()
    assert media is None
    assert erro == "Nenhum produto encontrado."


def test_rotas_produtos_cliente_venda(app_client):
    response = app_client.post("/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5})
    assert response.status_code == 201
    produto_id = response.get_json()["id"]

    response = app_client.post("/clientes", json={"nome": "João", "telefone": "12345"})
    assert response.status_code == 201
    cliente_id = response.get_json()["id"]

    response = app_client.post("/venda", json={"cliente_id": cliente_id, "produto_id": produto_id, "quantidade": 2, "forma_pagamento_id": 1})
    assert response.status_code == 201
    response_data = response.get_json()
    assert response_data["total"] == 21.0
    assert response_data["venda_id"] == 1
    assert db.session.get(Venda, response_data["venda_id"]) is not None
    movimentacao = db.session.query(MovimentacaoEstoque).one()
    assert movimentacao.venda_id == response_data["venda_id"]
    assert movimentacao.quantidade == 2
    assert movimentacao.saldo_anterior == 5
    assert movimentacao.saldo_atual == 3


def test_venda_com_preco_e_total_fracionarios(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Argamassa fracionaria", "preco": 10.55, "estoque": 5}
    ).get_json()
    cliente = app_client.post(
        "/clientes", json={"nome": "Cliente fracionario", "telefone": "12345"}
    ).get_json()

    response = app_client.post(
        "/venda",
        json={
            "cliente_id": cliente["id"],
            "produto_id": produto["id"],
            "quantidade": 3,
            "forma_pagamento_id": 1,
        },
    )

    assert response.status_code == 201
    response_data = response.get_json()
    assert response_data["total"] == 31.65

    venda = db.session.get(Venda, response_data["venda_id"])
    assert venda is not None
    assert venda.quantidade == 3
    assert float(venda.preco_unitario) == 10.55
    assert float(venda.total) == 31.65

    produto_atual = db.session.get(Produto, produto["id"])
    assert produto_atual is not None
    assert produto_atual.estoque == 2


def test_cadastro_bancario_e_vinculo_na_venda(app_client):
    response = app_client.post(
        "/contas-bancarias",
        json={
            "banco": "Banco Novo",
            "agencia": "1234",
            "numero": "98765-4",
            "tipo_conta": "poupanca",
            "titular": "Empresa Teste",
            "documento": "12.345.678/0001-90",
            "chave_pix": "financeiro@empresa.test",
        },
    )
    assert response.status_code == 201
    conta_id = response.get_json()["id"]

    contas = app_client.get("/contas-bancarias")
    assert contas.status_code == 200
    assert any(conta["id"] == conta_id for conta in contas.get_json()["contas"])

    produto = app_client.post(
        "/produtos", json={"nome": "Produto bancario", "preco": 10.55, "estoque": 2}
    ).get_json()
    cliente = app_client.post("/clientes", json={"nome": "Cliente bancario"}).get_json()
    venda = app_client.post(
        "/venda",
        json={
            "cliente_id": cliente["id"],
            "produto_id": produto["id"],
            "quantidade": 1,
            "forma_pagamento_id": 1,
            "conta_bancaria_id": conta_id,
        },
    )

    assert venda.status_code == 201
    venda_model = db.session.get(Venda, venda.get_json()["venda_id"])
    assert venda_model is not None
    assert venda_model.conta_bancaria_id == conta_id


def test_entrada_alimenta_estoque_e_fica_registrada(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Produto de entrada", "preco": 25.0, "estoque": 2}
    ).get_json()

    response = app_client.post(
        "/entradas-estoque",
        json={
            "produto_id": produto["id"],
            "quantidade": 8,
            "custo_unitario": 17.35,
            "origem": "Fornecedor Teste",
            "documento": "NF-123",
            "observacao": "Reposição inicial",
        },
    )

    assert response.status_code == 201
    dados = response.get_json()
    assert dados["saldo_anterior"] == 2
    assert dados["saldo_atual"] == 10

    produto_atual = db.session.get(Produto, produto["id"])
    assert produto_atual is not None
    assert produto_atual.estoque == 10
    entrada = db.session.get(EntradaEstoque, dados["id"])
    assert entrada is not None
    assert float(entrada.custo_unitario) == 17.35


def test_fornecedor_e_vinculo_na_entrada(app_client):
    fornecedor = app_client.post(
        "/fornecedores",
        json={
            "nome": "Fornecedor Cadastrado",
            "documento": "12.345.678/0001-90",
            "telefone": "1133334444",
            "email": "compras@fornecedor.test",
        },
    )
    assert fornecedor.status_code == 201
    fornecedor_id = fornecedor.get_json()["id"]
    assert app_client.get("/fornecedores").get_json()["fornecedores"][0]["id"] == fornecedor_id

    produto = app_client.post(
        "/produtos", json={"nome": "Produto fornecedor", "preco": 30.0, "estoque": 0}
    ).get_json()
    entrada = app_client.post(
        "/entradas-estoque",
        json={
            "produto_id": produto["id"],
            "fornecedor_id": fornecedor_id,
            "quantidade": 4,
            "custo_unitario": 22.50,
            "documento": "NF-456",
        },
    )
    assert entrada.status_code == 201
    entrada_model = db.session.get(EntradaEstoque, entrada.get_json()["id"])
    assert entrada_model is not None
    assert entrada_model.fornecedor_id == fornecedor_id
    assert db.session.get(Fornecedor, fornecedor_id) is not None


def test_inventario_controla_saldo_e_limites(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Produto inventario", "preco": 30.0, "estoque": 2}
    ).get_json()

    inventario = app_client.get("/inventario")
    assert inventario.status_code == 200
    registro = next(item for item in inventario.get_json()["inventario"] if item["produto_id"] == produto["id"])
    assert registro["estoque_atual"] == 2
    assert registro["status"] == "sem_custo"

    limites = app_client.patch(
        f"/inventario/{produto['id']}",
        json={"estoque_minimo": 1, "estoque_maximo": 10},
    )
    assert limites.status_code == 200

    entrada = app_client.post(
        "/entradas-estoque",
        json={"produto_id": produto["id"], "quantidade": 8, "custo_unitario": 20.0},
    )
    assert entrada.status_code == 201
    inventario_model = db.session.scalar(
        db.select(Inventario).where(Inventario.produto_id == produto["id"])
    )
    assert inventario_model is not None
    assert inventario_model.estoque_atual == 10
    assert float(inventario_model.custo_medio) == 16.0


def test_rota_media_precos(app_client):
    app_client.post("/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5})
    app_client.post("/produtos", json={"nome": "Cimento", "preco": 20.0, "estoque": 3})

    response = app_client.get("/operacoes/media-precos")
    assert response.status_code == 200
    assert response.get_json()["media_precos"] == 15.25


def test_resumo_vendas_diario(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5}
    ).get_json()
    cliente = app_client.post(
        "/clientes", json={"nome": "Cliente", "telefone": "12345"}
    ).get_json()
    app_client.post(
        "/venda",
        json={
            "cliente_id": cliente["id"],
            "produto_id": produto["id"],
            "quantidade": 2,
            "forma_pagamento_id": 1,
        },
    )

    response = app_client.get("/vendas/resumo?periodo=diario")

    assert response.status_code == 200
    assert response.get_json()["total_vendas"] == 21.0
    assert response.get_json()["quantidade_vendas"] == 1
    assert response.get_json()["quantidade_itens"] == 2


def test_cancelamento_nao_afeta_estoque_nem_vendas(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5}
    ).get_json()
    cliente = app_client.post(
        "/clientes", json={"nome": "Cliente", "telefone": "12345"}
    ).get_json()
    pedido = app_client.post(
        "/pedidos",
        json={"cliente_id": cliente["id"], "produto_id": produto["id"], "quantidade": 2},
    ).get_json()

    response = app_client.patch(f"/pedidos/{pedido['pedido_id']}/cancelar")

    assert response.status_code == 200
    assert db.session.get(Venda, 1) is None
    assert db.session.query(MovimentacaoEstoque).count() == 0
    produto_atual = db.session.get(Produto, produto["id"])
    assert produto_atual is not None
    assert produto_atual.estoque == 5


def test_relatorio_mostra_efetivadas_e_canceladas(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5}
    ).get_json()
    cliente = app_client.post(
        "/clientes", json={"nome": "Cliente", "telefone": "12345"}
    ).get_json()
    efetivada = app_client.post(
        "/venda",
        json={
            "cliente_id": cliente["id"],
            "produto_id": produto["id"],
            "quantidade": 1,
            "forma_pagamento_id": 1,
        },
    )
    pedido = app_client.post(
        "/pedidos",
        json={"cliente_id": cliente["id"], "produto_id": produto["id"], "quantidade": 1},
    ).get_json()
    app_client.patch(
        f"/pedidos/{pedido['pedido_id']}/cancelar",
        json={"motivo": "Pagamento não realizado"},
    )

    response = app_client.get("/relatorios/vendas")
    dados = response.get_json()

    assert efetivada.status_code == 201
    assert response.status_code == 200
    assert dados["quantidade_registros"] == 2
    assert dados["total_efetivado"] == 10.5
    assert dados["total_cancelado"] == 10.5
    assert {registro["status"] for registro in dados["registros"]} == {"efetivada", "cancelada"}
    cancelada = app_client.get("/relatorios/vendas?status=cancelada").get_json()
    assert cancelada["quantidade_registros"] == 1
    assert cancelada["registros"][0]["motivo_cancelamento"] == "Pagamento não realizado"


def test_health_publico(app_client):
    response = app_client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_simulador_frontend_esta_disponivel(app_client):
    response = app_client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True).lower()
    assert "simulador" in body or "argamassa" in body


def test_validacao_produto(app_client):
    response = app_client.post("/produtos", json={"nome": "", "preco": -1, "estoque": -2})
    assert response.status_code == 400


def test_venda_com_quantidade_invalida(app_client):
    response = app_client.post("/venda", json={"cliente_id": 1, "produto_id": 1, "quantidade": 0})
    assert response.status_code == 400


def test_venda_com_pagamento_invalido_nao_deixa_pedido_aberto(app_client):
    produto = app_client.post(
        "/produtos", json={"nome": "Argamassa", "preco": 10.5, "estoque": 5}
    ).get_json()
    cliente = app_client.post(
        "/clientes", json={"nome": "Cliente", "telefone": "12345"}
    ).get_json()

    response = app_client.post(
        "/venda",
        json={
            "cliente_id": cliente["id"],
            "produto_id": produto["id"],
            "quantidade": 1,
            "forma_pagamento_id": 999,
        },
    )

    assert response.status_code == 400
    assert db.session.query(Pedido).count() == 0
    assert db.session.query(Venda).count() == 0


def test_cancelamento_rejeita_json_nao_objeto(app_client):
    response = app_client.patch("/pedidos/1/cancelar", json=["motivo"])

    assert response.status_code == 400
