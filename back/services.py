from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List
from decimal import Decimal, ROUND_HALF_UP
import logging

from sqlalchemy import func, select, update

try:
    from .models import (
        db, Produto, Inventario, Cliente, Pedido, Venda, FormaPagamento, ContaBancaria, EntradaEstoque, Fornecedor,
        MovimentacaoEstoque, RelatorioVenda,
    )
except ImportError:  # pragma: no cover
    from models import (
        db, Produto, Inventario, Cliente, Pedido, Venda, FormaPagamento, ContaBancaria, EntradaEstoque, Fornecedor,
        MovimentacaoEstoque, RelatorioVenda,
    )

logger = logging.getLogger(__name__)


def criar_produto(nome: str, preco: float, estoque: int = 0) -> Produto:
    produto = Produto(nome=nome.strip(), preco=Decimal(str(preco)).quantize(Decimal("0.01")), estoque=estoque)
    try:
        db.session.add(produto)
        db.session.flush()
        db.session.add(Inventario(produto=produto))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return produto


def sincronizar_inventario(produto: Produto, estoque_atual: int) -> Inventario:
    with db.session.no_autoflush:
        inventario = db.session.scalar(select(Inventario).where(Inventario.produto_id == produto.id))
    if inventario is None:
        inventario = Inventario(produto=produto, estoque_atual=estoque_atual)
        db.session.add(inventario)
    else:
        inventario.estoque_atual = estoque_atual
    return inventario


def registrar_entrada_estoque(
    produto_id: int,
    quantidade: int,
    custo_unitario: float,
    fornecedor_id: Optional[int] = None,
    origem: Optional[str] = None,
    documento: Optional[str] = None,
    observacao: Optional[str] = None,
) -> Tuple[Optional[EntradaEstoque], Optional[str]]:
    if not isinstance(quantidade, int) or quantidade <= 0:
        return None, "Quantidade deve ser um número inteiro maior que zero."
    if custo_unitario < 0:
        return None, "Custo unitário não pode ser negativo."

    produto = db.session.get(Produto, produto_id)
    if produto is None:
        return None, "Produto não encontrado."
    fornecedor = None
    if fornecedor_id is not None:
        fornecedor = db.session.get(Fornecedor, fornecedor_id)
        if fornecedor is None or not fornecedor.ativo:
            return None, "Fornecedor não encontrado ou inativo."

    saldo_anterior = produto.estoque
    saldo_atual = db.session.execute(
        update(Produto)
        .where(Produto.id == produto_id)
        .values(estoque=Produto.estoque + quantidade)
        .returning(Produto.estoque)
    ).scalar_one()
    entrada = EntradaEstoque(
        produto=produto,
        fornecedor=fornecedor,
        quantidade=quantidade,
        custo_unitario=Decimal(str(custo_unitario)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        saldo_anterior=saldo_anterior,
        saldo_atual=saldo_atual,
        origem=origem,
        documento=documento,
        observacao=observacao,
    )
    try:
        inventario = sincronizar_inventario(produto, saldo_atual)
        custo_anterior = inventario.custo_medio or Decimal("0")
        quantidade_anterior = saldo_anterior
        quantidade_total = quantidade_anterior + quantidade
        if quantidade_total > 0:
            inventario.custo_medio = (
                (custo_anterior * quantidade_anterior + entrada.custo_unitario * quantidade)
                / quantidade_total
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        db.session.add(entrada)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Falha ao registrar entrada de estoque")
        return None, "Não foi possível registrar a entrada de estoque."
    return entrada, None


def criar_cliente(nome: str, telefone: Optional[str] = None) -> Cliente:
    cliente = Cliente(nome=nome, telefone=telefone)
    db.session.add(cliente)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return cliente


def criar_pedido(cliente_id: int, produto_id: int, quantidade: int) -> Tuple[Optional[Pedido], Optional[str]]:
    if cliente_id is None or produto_id is None or quantidade is None:
        return None, "cliente_id, produto_id e quantidade são obrigatórios."
    if not isinstance(quantidade, int) or quantidade <= 0:
        return None, "Quantidade deve ser um número inteiro maior que zero."

    cliente = db.session.get(Cliente, cliente_id)
    produto = db.session.get(Produto, produto_id)
    if cliente is None or produto is None:
        return None, "Cliente ou produto não encontrado."

    total = (Decimal(str(produto.preco)) * quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    pedido = Pedido(cliente=cliente, produto=produto, quantidade=quantidade, total=total)
    try:
        db.session.add(pedido)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Falha ao criar pedido")
        return None, "Não foi possível criar o pedido."
    return pedido, None


def efetivar_pedido(
    pedido_id: int,
    forma_pagamento_id: int,
    conta_bancaria_id: Optional[int] = None,
) -> Tuple[Optional[Pedido], Optional[str]]:
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        return None, "Pedido não encontrado."
    if pedido.status != "aberto":
        return None, "Somente pedidos abertos podem ser efetivados."

    forma_pagamento = db.session.get(FormaPagamento, forma_pagamento_id)
    if forma_pagamento is None or not forma_pagamento.ativo:
        return None, "Forma de pagamento não encontrada ou inativa."

    contas_ativas = db.session.scalars(
        select(ContaBancaria).where(ContaBancaria.ativa.is_(True)).order_by(ContaBancaria.id)
    ).all()
    conta_bancaria = None
    if conta_bancaria_id is not None:
        conta_bancaria = db.session.get(ContaBancaria, conta_bancaria_id)
        if conta_bancaria is None or not conta_bancaria.ativa:
            return None, "Conta bancária não encontrada ou inativa."
    elif len(contas_ativas) == 1:
        conta_bancaria = contas_ativas[0]
    elif len(contas_ativas) == 0:
        return None, "Cadastre uma conta bancária antes de concluir a venda."
    else:
        return None, "Informe a conta bancária de destino da venda."

    saldo_atual = db.session.execute(
        update(Produto)
        .where(Produto.id == pedido.produto_id, Produto.estoque >= pedido.quantidade)
        .values(estoque=Produto.estoque - pedido.quantidade)
        .returning(Produto.estoque)
    ).scalar_one_or_none()
    if saldo_atual is None:
        db.session.rollback()
        return None, "Estoque insuficiente."

    pedido.status = "efetivado"
    try:
        sincronizar_inventario(pedido.produto, saldo_atual)
        db.session.flush()
        evento_em = datetime.now(timezone.utc)
        venda = Venda(
            pedido=pedido,
            forma_pagamento=forma_pagamento,
            efetivada_em=evento_em,
            conta_bancaria=conta_bancaria,
        )
        db.session.add(venda)
        db.session.flush()
        db.session.add(MovimentacaoEstoque(
            venda=venda,
            saldo_anterior=saldo_atual + pedido.quantidade,
            saldo_atual=saldo_atual,
        ))
        db.session.add(RelatorioVenda(pedido=pedido, evento_em=evento_em))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Falha ao registrar venda")
        return None, "Não foi possível registrar a venda."
    return pedido, None


def registrar_venda(
    cliente_id: int,
    produto_id: int,
    quantidade: int,
    forma_pagamento_id: int,
    conta_bancaria_id: Optional[int] = None,
) -> Tuple[Optional[Pedido], Optional[str]]:
    pedido, error = criar_pedido(cliente_id, produto_id, quantidade)
    if error is not None:
        return None, error
    assert pedido is not None
    efetivado, error = efetivar_pedido(pedido.id, forma_pagamento_id, conta_bancaria_id)
    if error is not None:
        db.session.delete(pedido)
        db.session.commit()
        return None, error
    return efetivado, None


def cancelar_pedido(pedido_id: int, motivo: Optional[str] = None) -> Tuple[Optional[Pedido], Optional[str]]:
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        return None, "Pedido não encontrado."
    if pedido.status != "aberto":
        return None, "Somente pedidos abertos podem ser cancelados."

    pedido.status = "cancelado"
    try:
        relatorio = RelatorioVenda(pedido=pedido, evento_em=datetime.now(timezone.utc))
        relatorio.motivo_cancelamento = motivo
        db.session.add(relatorio)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Falha ao cancelar pedido")
        return None, "Não foi possível cancelar o pedido."
    return pedido, None


def resumo_vendas(periodo: str) -> dict[str, object]:
    agora = datetime.now(timezone.utc)
    inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    if periodo == "semanal":
        inicio -= timedelta(days=inicio.weekday())
    elif periodo == "mensal":
        inicio = inicio.replace(day=1)

    if periodo == "mensal":
        if inicio.month == 12:
            fim = inicio.replace(year=inicio.year + 1, month=1)
        else:
            fim = inicio.replace(month=inicio.month + 1)
    elif periodo == "semanal":
        fim = inicio + timedelta(days=7)
    else:
        fim = inicio + timedelta(days=1)

    total, quantidade_vendas, quantidade_itens = db.session.execute(
        select(
            func.coalesce(func.sum(Venda.total), 0),
            func.count(Venda.id),
            func.coalesce(func.sum(Venda.quantidade), 0),
        ).where(Venda.efetivada_em >= inicio, Venda.efetivada_em < fim)
    ).one()
    return {
        "periodo": periodo,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "total_vendas": round(float(total), 2),
        "quantidade_vendas": int(quantidade_vendas),
        "quantidade_itens": int(quantidade_itens),
    }


def relatorio_vendas(status: Optional[str] = None) -> dict[str, object]:
    consulta = select(RelatorioVenda).order_by(RelatorioVenda.criado_em.desc())
    if status is not None:
        consulta = consulta.where(RelatorioVenda.status == status)
    registros = db.session.scalars(consulta).all()
    efetivadas = [registro for registro in registros if registro.status == "efetivada"]
    canceladas = [registro for registro in registros if registro.status == "cancelada"]

    return {
        "quantidade_registros": len(registros),
        "total_efetivado": round(sum(float(registro.total) for registro in efetivadas), 2),
        "total_cancelado": round(sum(float(registro.total) for registro in canceladas), 2),
        "registros": [
            {
                "relatorio_id": registro.id,
                "pedido_id": registro.pedido_id,
                "cliente_id": registro.cliente_id,
                "produto_id": registro.produto_id,
                "status": registro.status,
                "quantidade": registro.quantidade,
                "total": float(registro.total),
                "criado_em": registro.criado_em.isoformat(),
                "efetivado_em": registro.efetivado_em.isoformat() if registro.efetivado_em else None,
                "cancelado_em": registro.cancelado_em.isoformat() if registro.cancelado_em else None,
                "motivo_cancelamento": registro.motivo_cancelamento,
            }
            for registro in registros
        ],
    }


# ===== OPERAÇÕES MATEMÁTICAS =====

def soma(valores: List[float]) -> float:
    """Calcula a soma de uma lista de valores."""
    return sum(valores)


def subtracao(valor1: float, valor2: float) -> float:
    """Calcula a subtração entre dois valores."""
    return valor1 - valor2


def multiplicacao(valor1: float, valor2: float) -> float:
    """Calcula a multiplicação entre dois valores."""
    return valor1 * valor2


def divisao(dividendo: float, divisor: float) -> Tuple[Optional[float], Optional[str]]:
    """Calcula a divisão entre dois valores com validação de divisão por zero."""
    if divisor == 0:
        return None, "Erro: divisão por zero não é permitida."
    return dividendo / divisor, None


def calcular_desconto(preco: float, percentual_desconto: float) -> Tuple[float, float]:
    """Calcula o valor do desconto e o preço final.
    Retorna (desconto, preco_final)
    """
    if percentual_desconto < 0 or percentual_desconto > 100:
        raise ValueError("Percentual de desconto deve estar entre 0 e 100.")
    
    desconto = preco * (percentual_desconto / 100)
    preco_final = preco - desconto
    return desconto, preco_final


def calcular_margem_lucro(custo: float, margem_percentual: float) -> Tuple[float, float]:
    """Calcula o preço de venda com margem de lucro.
    Retorna (margem_valor, preco_venda)
    """
    if margem_percentual < 0:
        raise ValueError("Margem de lucro não pode ser negativa.")
    
    margem_valor = custo * (margem_percentual / 100)
    preco_venda = custo + margem_valor
    return margem_valor, preco_venda


def calcular_media_precos(produto_ids: Optional[List[int]] = None) -> Tuple[Optional[float], Optional[str]]:
    """Calcula a média de preços dos produtos.
    Se produto_ids for None, calcula para todos os produtos.
    """
    try:
        if produto_ids is None:
            produtos = db.session.scalars(select(Produto)).all()
        else:
            assert produto_ids is not None
            produtos = db.session.scalars(
                select(Produto).where(Produto.id.in_(produto_ids))
            ).all()

        if not produtos:
            return None, "Nenhum produto encontrado."

        precos = [float(p.preco) for p in produtos]
        media = soma(precos) / len(precos)
        return media, None
    except Exception:
        logger.exception("Falha ao calcular média de preços")
        return None, "Não foi possível calcular a média de preços."

