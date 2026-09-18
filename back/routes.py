from flask import Blueprint, request, jsonify, Response, current_app, render_template
import hmac
import math
from typing import Any, Dict, Optional

try:
    from .models import ContaBancaria, EntradaEstoque, Fornecedor, Inventario, Produto, db
    from .services import (
        criar_produto, criar_cliente, criar_pedido, efetivar_pedido, registrar_venda,
        registrar_entrada_estoque,
        cancelar_pedido,
        resumo_vendas,
        relatorio_vendas,
        soma, subtracao, multiplicacao, divisao,
        calcular_desconto, calcular_margem_lucro,
        calcular_media_precos
    )
except ImportError:  # pragma: no cover
    from models import ContaBancaria, EntradaEstoque, Fornecedor, Inventario, Produto, db
    from services import (
        criar_produto, criar_cliente, criar_pedido, efetivar_pedido, registrar_venda,
        registrar_entrada_estoque,
        cancelar_pedido,
        resumo_vendas,
        relatorio_vendas,
        soma, subtracao, multiplicacao, divisao,
        calcular_desconto, calcular_margem_lucro,
        calcular_media_precos
    )

bp = Blueprint("main", __name__)


@bp.route("/fornecedores", methods=["POST"])
def add_fornecedor() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    nome = data.get("nome")
    documento = data.get("documento")
    if not isinstance(nome, str) or not nome.strip() or not isinstance(documento, str) or not documento.strip():
        return jsonify({"msg": "Nome e documento do fornecedor são obrigatórios."}), 400
    if len(nome.strip()) > 120 or len(documento.strip()) > 20:
        return jsonify({"msg": "Nome ou documento do fornecedor excede o limite."}), 400

    fornecedor = Fornecedor(
        nome=nome,
        documento=documento,
        telefone=data.get("telefone"),
        email=data.get("email"),
        endereco=data.get("endereco"),
        ativo=data.get("ativo", True),
    )
    try:
        db.session.add(fornecedor)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Não foi possível cadastrar o fornecedor. Documento já cadastrado?"}), 409
    return jsonify({"msg": "Fornecedor cadastrado com sucesso!", "id": fornecedor.id}), 201


@bp.route("/fornecedores", methods=["GET"])
def list_fornecedores() -> tuple[Response, int]:
    fornecedores = db.session.scalars(db.select(Fornecedor).order_by(Fornecedor.nome)).all()
    return jsonify({"fornecedores": [
        {
            "id": fornecedor.id,
            "nome": fornecedor.nome,
            "documento": fornecedor.documento,
            "telefone": fornecedor.telefone,
            "email": fornecedor.email,
            "endereco": fornecedor.endereco,
            "ativo": fornecedor.ativo,
        }
        for fornecedor in fornecedores
    ]}), 200


@bp.route("/inventario", methods=["GET"])
def list_inventario() -> tuple[Response, int]:
    registros = db.session.scalars(
        db.select(Inventario).join(Inventario.produto).order_by(Produto.nome)
    ).all()
    return jsonify({"inventario": [
        {
            "id": registro.id,
            "produto_id": registro.produto_id,
            "produto": registro.produto.nome,
            "estoque_atual": registro.estoque_atual,
            "estoque_minimo": registro.estoque_minimo,
            "estoque_maximo": registro.estoque_maximo,
            "custo_medio": float(registro.custo_medio) if registro.custo_medio is not None else None,
            "status": (
                "sem_custo" if registro.custo_medio is None
                else "critico" if registro.estoque_atual <= registro.estoque_minimo
                else "normal"
            ),
            "atualizado_em": registro.atualizado_em.isoformat(),
        }
        for registro in registros
    ]}), 200


@bp.route("/inventario/<int:produto_id>", methods=["PATCH"])
def update_inventario(produto_id: int) -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None
    inventario = db.session.scalar(
        db.select(Inventario).where(Inventario.produto_id == produto_id)
    )
    if inventario is None:
        return jsonify({"msg": "Produto não encontrado no inventário."}), 404

    for field in ("estoque_minimo", "estoque_maximo"):
        if field in data:
            value, error = _extract_int(data[field], field)
            if error or value is None or value < 0:
                return jsonify({"msg": error or f"{field} deve ser maior ou igual a zero."}), 400
            setattr(inventario, field, value)
    if inventario.estoque_maximo is not None and inventario.estoque_maximo < inventario.estoque_minimo:
        return jsonify({"msg": "Estoque máximo deve ser maior ou igual ao estoque mínimo."}), 400
    db.session.commit()
    return jsonify({"msg": "Parâmetros de inventário atualizados!", "produto_id": produto_id}), 200


@bp.before_request
def require_api_key() -> Optional[tuple[Response, int]]:
    if request.endpoint in {"main.health", "main.index"} or current_app.config.get("TESTING"):
        return None
    expected = current_app.config.get("API_KEY")
    provided = request.headers.get("X-API-Key", "")
    if not expected or not hmac.compare_digest(provided, expected):
        return jsonify({"msg": "Não autorizado."}), 401
    return None


@bp.route("/", methods=["GET"])
def index() -> tuple[Response, int]:
    response = Response(render_template("index.html", api_key=current_app.config.get("API_KEY", "demo-api-key")))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response, 200


@bp.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    return jsonify({"status": "ok"}), 200


def _json_payload() -> tuple[Optional[Dict[str, Any]], Optional[tuple[Response, int]]]:
    payload = request.get_json(silent=True)
    if payload is None:
        return None, (jsonify({"msg": "JSON inválido ou corpo vazio."}), 400)
    if not isinstance(payload, dict):
        return None, (jsonify({"msg": "JSON deve ser um objeto."}), 400)
    return payload, None


def _extract_int(value: Any, name: str) -> tuple[Optional[int], Optional[str]]:
    if isinstance(value, bool):
        return None, f"{name} inválido."
    if isinstance(value, int):
        return value, None
    return None, f"{name} deve ser um número inteiro."


def _extract_float(value: Any, name: str) -> tuple[Optional[float], Optional[str]]:
    if isinstance(value, bool):
        return None, f"{name} inválido."
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value), None
    return None, f"{name} deve ser um número."


def _extract_number_list(values: Any, name: str) -> tuple[Optional[list[float]], Optional[str]]:
    if not isinstance(values, list) or not values:
        return None, f"{name} deve ser uma lista de números."
    result: list[float] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            return None, f"Todos os itens de {name} devem ser números."
        result.append(float(item))
    return result, None


@bp.route("/produtos", methods=["POST"])
def add_produto() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    nome = data.get("nome")
    preco = data.get("preco")
    estoque = data.get("estoque", 0)

    if not isinstance(nome, str) or not nome.strip() or len(nome.strip()) > 100:
        return jsonify({"msg": "Nome do produto é obrigatório."}), 400

    preco_valido, preco_erro = _extract_float(preco, "Preço")
    if preco_erro is not None:
        return jsonify({"msg": preco_erro}), 400
    assert preco_valido is not None

    estoque_valido, estoque_erro = _extract_int(estoque, "Estoque")
    if estoque_erro is not None:
        return jsonify({"msg": estoque_erro}), 400
    assert estoque_valido is not None
    if preco_valido < 0 or estoque_valido < 0:
        return jsonify({"msg": "Preço e estoque não podem ser negativos."}), 400

    produto = criar_produto(nome, preco_valido, estoque_valido)
    return jsonify({"msg": "Produto cadastrado com sucesso!", "id": produto.id}), 201


@bp.route("/entradas-estoque", methods=["POST"])
def add_entrada_estoque() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    produto_id, produto_id_erro = _extract_int(data.get("produto_id"), "produto_id")
    fornecedor_id = data.get("fornecedor_id")
    if fornecedor_id is not None:
        fornecedor_id, fornecedor_id_erro = _extract_int(fornecedor_id, "fornecedor_id")
        if fornecedor_id_erro:
            return jsonify({"msg": fornecedor_id_erro}), 400
    quantidade, quantidade_erro = _extract_int(data.get("quantidade"), "quantidade")
    custo, custo_erro = _extract_float(data.get("custo_unitario"), "custo_unitario")
    if produto_id_erro or quantidade_erro or custo_erro:
        return jsonify({"msg": produto_id_erro or quantidade_erro or custo_erro}), 400
    assert produto_id is not None and quantidade is not None and custo is not None
    if quantidade <= 0 or custo < 0:
        return jsonify({"msg": "Quantidade deve ser maior que zero e custo não pode ser negativo."}), 400

    entrada, error = registrar_entrada_estoque(
        produto_id,
        quantidade,
        custo,
        fornecedor_id,
        data.get("origem"),
        data.get("documento"),
        data.get("observacao"),
    )
    if error is not None:
        return jsonify({"msg": error}), 400
    assert entrada is not None
    return jsonify({
        "msg": "Entrada de estoque registrada!",
        "id": entrada.id,
        "produto_id": entrada.produto_id,
        "saldo_anterior": entrada.saldo_anterior,
        "saldo_atual": entrada.saldo_atual,
    }), 201


@bp.route("/entradas-estoque", methods=["GET"])
def list_entradas_estoque() -> tuple[Response, int]:
    entradas = db.session.scalars(
        db.select(EntradaEstoque).order_by(EntradaEstoque.criado_em.desc())
    ).all()
    return jsonify({"entradas": [
        {
            "id": entrada.id,
            "produto_id": entrada.produto_id,
            "fornecedor_id": entrada.fornecedor_id,
            "fornecedor": entrada.fornecedor.nome if entrada.fornecedor else None,
            "produto": entrada.produto.nome,
            "quantidade": entrada.quantidade,
            "custo_unitario": float(entrada.custo_unitario),
            "origem": entrada.origem,
            "documento": entrada.documento,
            "observacao": entrada.observacao,
            "saldo_anterior": entrada.saldo_anterior,
            "saldo_atual": entrada.saldo_atual,
            "criado_em": entrada.criado_em.isoformat(),
        }
        for entrada in entradas
    ]}), 200


@bp.route("/clientes", methods=["POST"])
def add_cliente() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    nome = data.get("nome")
    telefone = data.get("telefone")

    if not isinstance(nome, str) or not nome.strip() or len(nome.strip()) > 100:
        return jsonify({"msg": "Nome do cliente é obrigatório."}), 400
    if telefone is not None and (not isinstance(telefone, str) or len(telefone) > 20):
        return jsonify({"msg": "Telefone deve ser uma string."}), 400

    cliente = criar_cliente(nome, telefone)
    return jsonify({"msg": "Cliente cadastrado com sucesso!", "id": cliente.id}), 201


@bp.route("/contas-bancarias", methods=["POST"])
def add_conta_bancaria() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    campos_obrigatorios = ("banco", "agencia", "numero", "tipo_conta", "titular")
    if any(not isinstance(data.get(campo), str) or not data[campo].strip() for campo in campos_obrigatorios):
        return jsonify({"msg": "Banco, agência, número, tipo de conta e titular são obrigatórios."}), 400

    tipo_conta = data["tipo_conta"].strip().lower()
    if tipo_conta not in {"corrente", "poupanca", "pagamento"}:
        return jsonify({"msg": "Tipo de conta deve ser corrente, poupanca ou pagamento."}), 400

    conta = ContaBancaria(
        banco=data["banco"],
        agencia=data["agencia"],
        numero=data["numero"],
        tipo_conta=tipo_conta,
        titular=data["titular"],
        documento=data.get("documento"),
        chave_pix=data.get("chave_pix"),
        ativa=data.get("ativa", True),
    )
    try:
        db.session.add(conta)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Não foi possível cadastrar a conta bancária."}), 409
    return jsonify({"msg": "Conta bancária cadastrada com sucesso!", "id": conta.id}), 201


@bp.route("/contas-bancarias", methods=["GET"])
def list_contas_bancarias() -> tuple[Response, int]:
    contas = db.session.scalars(
        db.select(ContaBancaria).order_by(ContaBancaria.id)
    ).all()
    return jsonify({
        "contas": [
            {
                "id": conta.id,
                "banco": conta.banco,
                "agencia": conta.agencia,
                "numero": conta.numero,
                "tipo_conta": conta.tipo_conta,
                "titular": conta.titular,
                "documento": conta.documento,
                "chave_pix": conta.chave_pix,
                "ativa": conta.ativa,
            }
            for conta in contas
        ]
    }), 200


@bp.route("/venda", methods=["POST"])
def registrar_venda_route() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    cliente_id, cliente_id_erro = _extract_int(data.get("cliente_id"), "cliente_id")
    produto_id, produto_id_erro = _extract_int(data.get("produto_id"), "produto_id")
    quantidade, quantidade_erro = _extract_int(data.get("quantidade"), "quantidade")
    forma_pagamento_id, forma_pagamento_erro = _extract_int(
        data.get("forma_pagamento_id"), "forma_pagamento_id"
    )
    conta_bancaria_id = data.get("conta_bancaria_id")
    if conta_bancaria_id is not None:
        conta_bancaria_id, conta_bancaria_erro = _extract_int(conta_bancaria_id, "conta_bancaria_id")
        if conta_bancaria_erro:
            return jsonify({"msg": conta_bancaria_erro}), 400

    if cliente_id_erro or produto_id_erro or quantidade_erro or forma_pagamento_erro:
        return jsonify({"msg": cliente_id_erro or produto_id_erro or quantidade_erro or forma_pagamento_erro}), 400
    assert cliente_id is not None
    assert produto_id is not None
    assert quantidade is not None
    assert forma_pagamento_id is not None
    if quantidade <= 0:
        return jsonify({"msg": "Quantidade deve ser maior que zero."}), 400

    pedido, error = registrar_venda(
        cliente_id, produto_id, quantidade, forma_pagamento_id, conta_bancaria_id
    )
    if error:
        return jsonify({"msg": error}), 400

    assert pedido is not None
    venda = pedido.venda
    assert venda is not None
    return jsonify({
        "msg": "Venda registrada!",
        "total": float(pedido.total),
        "pedido_id": pedido.id,
        "venda_id": venda.id,
    }), 201


@bp.route("/pedidos", methods=["POST"])
def criar_pedido_route() -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    cliente_id, cliente_id_erro = _extract_int(data.get("cliente_id"), "cliente_id")
    produto_id, produto_id_erro = _extract_int(data.get("produto_id"), "produto_id")
    quantidade, quantidade_erro = _extract_int(data.get("quantidade"), "quantidade")
    if cliente_id_erro or produto_id_erro or quantidade_erro:
        return jsonify({"msg": cliente_id_erro or produto_id_erro or quantidade_erro}), 400
    assert cliente_id is not None and produto_id is not None and quantidade is not None

    pedido, error = criar_pedido(cliente_id, produto_id, quantidade)
    if error is not None:
        return jsonify({"msg": error}), 400
    assert pedido is not None
    return jsonify({"msg": "Pedido criado!", "pedido_id": pedido.id, "status": pedido.status}), 201


@bp.route("/pedidos/<int:pedido_id>/efetivar", methods=["POST"])
def efetivar_pedido_route(pedido_id: int) -> tuple[Response, int]:
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None
    forma_pagamento_id, forma_pagamento_erro = _extract_int(
        data.get("forma_pagamento_id"), "forma_pagamento_id"
    )
    conta_bancaria_id = data.get("conta_bancaria_id")
    if conta_bancaria_id is not None:
        conta_bancaria_id, conta_bancaria_erro = _extract_int(conta_bancaria_id, "conta_bancaria_id")
        if conta_bancaria_erro:
            return jsonify({"msg": conta_bancaria_erro}), 400
    if forma_pagamento_erro is not None:
        return jsonify({"msg": forma_pagamento_erro}), 400
    assert forma_pagamento_id is not None

    pedido, error = efetivar_pedido(pedido_id, forma_pagamento_id, conta_bancaria_id)
    if error is not None:
        status_code = 404 if pedido is None and error == "Pedido não encontrado." else 400
        return jsonify({"msg": error}), status_code
    assert pedido is not None and pedido.venda is not None
    return jsonify({
        "msg": "Venda efetivada!",
        "pedido_id": pedido.id,
        "venda_id": pedido.venda.id,
        "total": float(pedido.total),
    }), 201


@bp.route("/pedidos/<int:pedido_id>/cancelar", methods=["PATCH"])
def cancelar_pedido_route(pedido_id: int) -> tuple[Response, int]:
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({"msg": "JSON deve ser um objeto."}), 400
    motivo = data.get("motivo")
    if motivo is not None and (not isinstance(motivo, str) or len(motivo) > 200):
        return jsonify({"msg": "Motivo deve ser uma string de até 200 caracteres."}), 400
    pedido, error = cancelar_pedido(pedido_id, motivo)
    if error is not None:
        status_code = 404 if pedido is None and error == "Pedido não encontrado." else 400
        return jsonify({"msg": error}), status_code
    assert pedido is not None
    return jsonify({"msg": "Pedido cancelado!", "pedido_id": pedido.id}), 200


@bp.route("/vendas/resumo", methods=["GET"])
def resumo_vendas_route() -> tuple[Response, int]:
    periodo = request.args.get("periodo", "diario").strip().lower()
    if periodo not in {"diario", "semanal", "mensal"}:
        return jsonify({"msg": "Período deve ser diario, semanal ou mensal."}), 400
    return jsonify(resumo_vendas(periodo)), 200


@bp.route("/relatorios/vendas", methods=["GET"])
def relatorio_vendas_route() -> tuple[Response, int]:
    status = request.args.get("status")
    if status not in {None, "efetivada", "cancelada"}:
        return jsonify({"msg": "Status deve ser efetivada ou cancelada."}), 400
    return jsonify(relatorio_vendas(status)), 200


# ===== ROTAS DE OPERAÇÕES MATEMÁTICAS =====

@bp.route("/operacoes/soma", methods=["POST"])
def rota_soma() -> tuple[Response, int]:
    """Calcula a soma de uma lista de valores.
    Esperado: {"valores": [1.5, 2.5, 3.0]}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    valores, erro = _extract_number_list(data.get("valores"), "valores")
    if erro is not None:
        return jsonify({"msg": erro}), 400
    assert valores is not None

    resultado = soma(valores)
    return jsonify({"resultado": resultado, "operacao": "soma"}), 200


@bp.route("/operacoes/subtracao", methods=["POST"])
def rota_subtracao() -> tuple[Response, int]:
    """Calcula a subtração entre dois valores.
    Esperado: {"valor1": 10, "valor2": 5}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    valor1, erro1 = _extract_float(data.get("valor1"), "valor1")
    valor2, erro2 = _extract_float(data.get("valor2"), "valor2")
    if erro1 or erro2:
        return jsonify({"msg": erro1 or erro2}), 400
    assert valor1 is not None
    assert valor2 is not None

    resultado = subtracao(valor1, valor2)
    return jsonify({"resultado": resultado, "operacao": "subtracao"}), 200


@bp.route("/operacoes/multiplicacao", methods=["POST"])
def rota_multiplicacao() -> tuple[Response, int]:
    """Calcula a multiplicação entre dois valores.
    Esperado: {"valor1": 10, "valor2": 5}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    valor1, erro1 = _extract_float(data.get("valor1"), "valor1")
    valor2, erro2 = _extract_float(data.get("valor2"), "valor2")
    if erro1 or erro2:
        return jsonify({"msg": erro1 or erro2}), 400
    assert valor1 is not None
    assert valor2 is not None

    resultado = multiplicacao(valor1, valor2)
    return jsonify({"resultado": resultado, "operacao": "multiplicacao"}), 200


@bp.route("/operacoes/divisao", methods=["POST"])
def rota_divisao() -> tuple[Response, int]:
    """Calcula a divisão entre dois valores.
    Esperado: {"dividendo": 10, "divisor": 2}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    dividendo, erro1 = _extract_float(data.get("dividendo"), "dividendo")
    divisor, erro2 = _extract_float(data.get("divisor"), "divisor")
    if erro1 or erro2:
        return jsonify({"msg": erro1 or erro2}), 400
    assert dividendo is not None
    assert divisor is not None

    resultado, erro = divisao(dividendo, divisor)
    if erro is not None:
        return jsonify({"msg": erro}), 400

    return jsonify({"resultado": resultado, "operacao": "divisao"}), 200


@bp.route("/operacoes/desconto", methods=["POST"])
def rota_desconto() -> tuple[Response, int]:
    """Calcula desconto em um preço.
    Esperado: {"preco": 100.0, "percentual_desconto": 10}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    preco, erro1 = _extract_float(data.get("preco"), "preco")
    percentual, erro2 = _extract_float(data.get("percentual_desconto"), "percentual_desconto")
    if erro1 or erro2:
        return jsonify({"msg": erro1 or erro2}), 400
    assert preco is not None
    assert percentual is not None

    try:
        desconto, preco_final = calcular_desconto(preco, percentual)
        return jsonify({
            "preco_original": preco,
            "percentual_desconto": percentual,
            "valor_desconto": round(desconto, 2),
            "preco_final": round(preco_final, 2),
            "operacao": "desconto"
        }), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400


@bp.route("/operacoes/margem-lucro", methods=["POST"])
def rota_margem_lucro() -> tuple[Response, int]:
    """Calcula preço de venda com margem de lucro.
    Esperado: {"custo": 50.0, "margem_percentual": 30}
    """
    data, error_response = _json_payload()
    if error_response is not None:
        return error_response
    assert data is not None

    custo, erro1 = _extract_float(data.get("custo"), "custo")
    margem, erro2 = _extract_float(data.get("margem_percentual"), "margem_percentual")
    if erro1 or erro2:
        return jsonify({"msg": erro1 or erro2}), 400
    assert custo is not None
    assert margem is not None

    try:
        margem_valor, preco_venda = calcular_margem_lucro(custo, margem)
        return jsonify({
            "custo": custo,
            "margem_percentual": margem,
            "valor_margem": round(margem_valor, 2),
            "preco_venda": round(preco_venda, 2),
            "operacao": "margem_lucro"
        }), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400


@bp.route("/operacoes/media-precos", methods=["GET"])
def rota_media_precos() -> tuple[Response, int]:
    """Calcula a média de preços dos produtos.
    Opcional: ?produto_ids=1,2,3 para filtrar por IDs
    """
    produto_ids_str = request.args.get("produto_ids")
    produto_ids = None

    if produto_ids_str:
        try:
            produto_ids = [int(id) for id in produto_ids_str.split(",")]
        except ValueError:
            return jsonify({"msg": "IDs de produtos inválidos."}), 400

    media, erro = calcular_media_precos(produto_ids)
    if erro is not None:
        return jsonify({"msg": erro}), 400

    if media is None:
        return jsonify({"msg": "Nenhum produto encontrado."}), 400

    return jsonify({
        "media_precos": round(float(media), 2),
        "operacao": "media_precos"
    }), 200
