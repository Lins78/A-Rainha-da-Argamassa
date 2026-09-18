from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from decimal import Decimal

db = SQLAlchemy()

class Produto(db.Model):
    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_produto_preco_nao_negativo"),
        CheckConstraint("estoque >= 0", name="ck_produto_estoque_nao_negativo"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    preco: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    estoque: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)

    def __init__(self, nome: str, preco: Decimal | float, estoque: int = 0) -> None:
        self.nome = nome
        self.preco = Decimal(str(preco))
        self.estoque = estoque


class Inventario(db.Model):
    __tablename__ = "inventario"
    __table_args__ = (
        CheckConstraint("estoque_atual >= 0", name="ck_inventario_estoque_atual_nao_negativo"),
        CheckConstraint("estoque_minimo >= 0", name="ck_inventario_estoque_minimo_nao_negativo"),
        CheckConstraint(
            "estoque_maximo IS NULL OR estoque_maximo >= estoque_minimo",
            name="ck_inventario_estoque_maximo_valido",
        ),
        CheckConstraint("custo_medio IS NULL OR custo_medio >= 0", name="ck_inventario_custo_medio_nao_negativo"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    produto_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("produto.id"), nullable=False, unique=True
    )
    estoque_atual: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    estoque_minimo: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    estoque_maximo: Mapped[Optional[int]] = mapped_column(db.Integer)
    custo_medio: Mapped[Optional[Decimal]] = mapped_column(db.Numeric(12, 2), nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    produto: Mapped[Produto] = relationship(
        "Produto", backref=db.backref("inventario", uselist=False)
    )

    def __init__(
        self,
        produto: Produto,
        estoque_atual: Optional[int] = None,
        estoque_minimo: int = 0,
        estoque_maximo: Optional[int] = None,
        custo_medio: Optional[Decimal | float] = None,
    ) -> None:
        self.produto = produto
        self.estoque_atual = produto.estoque if estoque_atual is None else estoque_atual
        self.estoque_minimo = estoque_minimo
        self.estoque_maximo = estoque_maximo
        self.custo_medio = Decimal(str(custo_medio)) if custo_medio is not None else None

class Cliente(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    telefone: Mapped[Optional[str]] = mapped_column(db.String(20))

    def __init__(self, nome: str, telefone: Optional[str] = None) -> None:
        self.nome = nome
        self.telefone = telefone


class FormaPagamento(db.Model):
    __tablename__ = "formas_pagamento"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(40), nullable=False, unique=True)
    ativo: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    vendas: Mapped[list["Venda"]] = relationship("Venda", back_populates="forma_pagamento")

    def __init__(self, nome: str, ativo: bool = True) -> None:
        self.nome = nome
        self.ativo = ativo


class ContaBancaria(db.Model):
    __tablename__ = "contas_bancarias"
    __table_args__ = (
        db.UniqueConstraint("banco", "agencia", "numero", name="uq_conta_bancaria_identificacao"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    banco: Mapped[str] = mapped_column(db.String(100), nullable=False)
    agencia: Mapped[str] = mapped_column(db.String(20), nullable=False)
    numero: Mapped[str] = mapped_column(db.String(30), nullable=False)
    tipo_conta: Mapped[str] = mapped_column(db.String(20), nullable=False, default="corrente")
    titular: Mapped[str] = mapped_column(db.String(100), nullable=False)
    documento: Mapped[Optional[str]] = mapped_column(db.String(20))
    chave_pix: Mapped[Optional[str]] = mapped_column(db.String(100))
    ativa: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    vendas: Mapped[list["Venda"]] = relationship("Venda", back_populates="conta_bancaria")

    def __init__(
        self,
        banco: str,
        agencia: str,
        numero: str,
        tipo_conta: str,
        titular: str,
        documento: Optional[str] = None,
        chave_pix: Optional[str] = None,
        ativa: bool = True,
    ) -> None:
        self.banco = banco.strip()
        self.agencia = agencia.strip()
        self.numero = numero.strip()
        self.tipo_conta = tipo_conta.strip().lower()
        self.titular = titular.strip()
        self.documento = documento.strip() if documento else None
        self.chave_pix = chave_pix.strip() if chave_pix else None
        self.ativa = ativa


class Pedido(db.Model):
    __tablename__ = "pedido"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_pedido_quantidade_positiva"),
        CheckConstraint("total >= 0", name="ck_pedido_total_nao_negativo"),
        CheckConstraint("status IN ('aberto', 'efetivado', 'cancelado')", name="ck_pedido_status_valido"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    total: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="aberto")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    cliente: Mapped[Cliente] = relationship("Cliente", backref="pedidos")
    produto: Mapped[Produto] = relationship("Produto", backref="pedidos")
    venda: Mapped[Optional["Venda"]] = relationship("Venda", back_populates="pedido", uselist=False)

    def __init__(self, cliente: Cliente, produto: Produto, quantidade: int, total: Decimal | float, status: str = "aberto") -> None:
        self.cliente = cliente
        self.produto = produto
        self.quantidade = quantidade
        self.total = Decimal(str(total))
        self.status = status


class Venda(db.Model):
    __tablename__ = "vendas"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_vendas_quantidade_positiva"),
        CheckConstraint("total >= 0", name="ck_vendas_total_nao_negativo"),
        CheckConstraint("preco_unitario >= 0", name="ck_vendas_preco_unitario_nao_negativo"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("pedido.id"), nullable=False, unique=True)
    cliente_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    forma_pagamento_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("formas_pagamento.id"), nullable=False)
    conta_bancaria_id: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("contas_bancarias.id"), nullable=True
    )
    quantidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    efetivada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pedido: Mapped[Pedido] = relationship("Pedido", back_populates="venda")
    cliente: Mapped[Cliente] = relationship("Cliente", backref="vendas")
    produto: Mapped[Produto] = relationship("Produto", backref="vendas")
    forma_pagamento: Mapped[FormaPagamento] = relationship("FormaPagamento", back_populates="vendas")
    conta_bancaria: Mapped[Optional[ContaBancaria]] = relationship("ContaBancaria", back_populates="vendas")

    def __init__(
        self,
        pedido: Pedido,
        forma_pagamento: FormaPagamento,
        efetivada_em: datetime,
        conta_bancaria: Optional[ContaBancaria] = None,
    ) -> None:
        self.pedido = pedido
        self.cliente_id = pedido.cliente_id
        self.produto_id = pedido.produto_id
        self.forma_pagamento = forma_pagamento
        self.conta_bancaria = conta_bancaria
        self.quantidade = pedido.quantidade
        self.preco_unitario = Decimal(str(pedido.total)) / pedido.quantidade
        self.total = pedido.total
        self.efetivada_em = efetivada_em


class Fornecedor(db.Model):
    __tablename__ = "fornecedores"
    __table_args__ = (
        db.UniqueConstraint("documento", name="uq_fornecedor_documento"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120), nullable=False)
    documento: Mapped[str] = mapped_column(db.String(20), nullable=False)
    telefone: Mapped[Optional[str]] = mapped_column(db.String(20))
    email: Mapped[Optional[str]] = mapped_column(db.String(120))
    endereco: Mapped[Optional[str]] = mapped_column(db.String(255))
    ativo: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    entradas: Mapped[list["EntradaEstoque"]] = relationship("EntradaEstoque", back_populates="fornecedor")

    def __init__(
        self,
        nome: str,
        documento: str,
        telefone: Optional[str] = None,
        email: Optional[str] = None,
        endereco: Optional[str] = None,
        ativo: bool = True,
    ) -> None:
        self.nome = nome.strip()
        self.documento = documento.strip()
        self.telefone = telefone.strip() if telefone else None
        self.email = email.strip() if email else None
        self.endereco = endereco.strip() if endereco else None
        self.ativo = ativo


class EntradaEstoque(db.Model):
    __tablename__ = "entradas_estoque"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_entrada_estoque_quantidade_positiva"),
        CheckConstraint("custo_unitario >= 0", name="ck_entrada_estoque_custo_nao_negativo"),
        CheckConstraint("saldo_anterior >= 0", name="ck_entrada_estoque_saldo_anterior_nao_negativo"),
        CheckConstraint("saldo_atual > saldo_anterior", name="ck_entrada_estoque_saldo_atual_valido"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    produto_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("fornecedores.id"), nullable=True
    )
    quantidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    custo_unitario: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    origem: Mapped[Optional[str]] = mapped_column(db.String(100))
    documento: Mapped[Optional[str]] = mapped_column(db.String(50))
    observacao: Mapped[Optional[str]] = mapped_column(db.String(255))
    saldo_anterior: Mapped[int] = mapped_column(db.Integer, nullable=False)
    saldo_atual: Mapped[int] = mapped_column(db.Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    produto: Mapped[Produto] = relationship("Produto", backref="entradas_estoque")
    fornecedor: Mapped[Optional[Fornecedor]] = relationship("Fornecedor", back_populates="entradas")

    def __init__(
        self,
        produto: Produto,
        quantidade: int,
        custo_unitario: Decimal | float,
        saldo_anterior: int,
        saldo_atual: int,
        fornecedor: Optional[Fornecedor] = None,
        origem: Optional[str] = None,
        documento: Optional[str] = None,
        observacao: Optional[str] = None,
    ) -> None:
        self.produto = produto
        self.fornecedor = fornecedor
        self.quantidade = quantidade
        self.custo_unitario = Decimal(str(custo_unitario))
        self.saldo_anterior = saldo_anterior
        self.saldo_atual = saldo_atual
        self.origem = origem.strip() if origem else None
        self.documento = documento.strip() if documento else None
        self.observacao = observacao.strip() if observacao else None


class MovimentacaoEstoque(db.Model):
    __tablename__ = "estoque"
    __table_args__ = (
        CheckConstraint("tipo = 'saida'", name="ck_estoque_tipo_saida"),
        CheckConstraint("quantidade > 0", name="ck_estoque_quantidade_positiva"),
        CheckConstraint("saldo_anterior >= 0", name="ck_estoque_saldo_anterior_nao_negativo"),
        CheckConstraint("saldo_atual >= 0", name="ck_estoque_saldo_atual_nao_negativo"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    produto_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    venda_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("vendas.id"), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(db.String(10), nullable=False, default="saida")
    quantidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    saldo_anterior: Mapped[int] = mapped_column(db.Integer, nullable=False)
    saldo_atual: Mapped[int] = mapped_column(db.Integer, nullable=False)
    movimentado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    produto: Mapped[Produto] = relationship("Produto", backref="movimentacoes_estoque")
    venda: Mapped[Venda] = relationship("Venda", backref="movimentacao_estoque")

    def __init__(self, venda: Venda, saldo_anterior: int, saldo_atual: int) -> None:
        self.produto = venda.produto
        self.venda = venda
        self.tipo = "saida"
        self.quantidade = venda.quantidade
        self.saldo_anterior = saldo_anterior
        self.saldo_atual = saldo_atual


class RelatorioVenda(db.Model):
    __tablename__ = "relatorios"
    __table_args__ = (
        CheckConstraint("status IN ('efetivada', 'cancelada')", name="ck_relatorio_status_valido"),
        CheckConstraint("quantidade > 0", name="ck_relatorio_quantidade_positiva"),
        CheckConstraint("total >= 0", name="ck_relatorio_total_nao_negativo"),
    )
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("pedido.id"), nullable=False, unique=True)
    cliente_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False)
    quantidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    total: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    efetivado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    motivo_cancelamento: Mapped[Optional[str]] = mapped_column(db.String(200))

    pedido: Mapped[Pedido] = relationship("Pedido", backref="relatorio")
    cliente: Mapped[Cliente] = relationship("Cliente", backref="relatorios_vendas")
    produto: Mapped[Produto] = relationship("Produto", backref="relatorios_vendas")

    def __init__(
        self,
        pedido: Pedido,
        evento_em: datetime,
    ) -> None:
        self.pedido = pedido
        self.cliente_id = pedido.cliente_id
        self.produto_id = pedido.produto_id
        self.status = "efetivada" if pedido.status == "efetivado" else "cancelada"
        self.quantidade = pedido.quantidade
        self.total = pedido.total
        self.criado_em = pedido.criado_em
        self.efetivado_em = evento_em if pedido.status == "efetivado" else None
        self.cancelado_em = evento_em if pedido.status == "cancelado" else None

