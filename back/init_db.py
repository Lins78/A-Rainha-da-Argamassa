"""Cria o banco PostgreSQL e as tabelas da aplicação."""

import os

import psycopg2
from sqlalchemy.engine import make_url

try:
    from .app import create_app
    from .config import Config
    from .models import db, FormaPagamento, Pedido, RelatorioVenda
except ImportError:  # pragma: no cover
    from app import create_app
    from config import Config
    from models import db, FormaPagamento, Pedido, RelatorioVenda


FORMAS_PAGAMENTO_PADRAO = (
    "Dinheiro",
    "Pix",
    "Cartão de crédito",
    "Cartão de débito",
    "Boleto bancário",
    "Transferência bancária",
)


def create_database() -> None:
    """Cria o banco principal se ele ainda não existir."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Defina DATABASE_URL com a conexão PostgreSQL.")

    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        raise RuntimeError("DATABASE_URL deve informar o nome do banco.")

    maintenance_url = url.set(database="postgres")
    connection = psycopg2.connect(
        host=maintenance_url.host,
        port=maintenance_url.port,
        user=maintenance_url.username,
        password=maintenance_url.password,
        dbname=maintenance_url.database,
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    'CREATE DATABASE "%s"' % database_name.replace('"', '""')
                )
                print(f"Banco '{database_name}' criado.")
            else:
                print(f"Banco '{database_name}' já existe.")
    finally:
        connection.close()


def create_tables() -> None:
    """Cria as tabelas e carrega dados iniciais apenas quando necessário."""
    app = create_app(Config)
    with app.app_context():
        db.create_all()

        for nome in FORMAS_PAGAMENTO_PADRAO:
            if db.session.query(FormaPagamento).filter_by(nome=nome).first() is None:
                db.session.add(FormaPagamento(nome=nome))

        pedidos_finais = db.session.query(Pedido).filter(
            Pedido.status.in_(("efetivado", "cancelado"))
        ).all()
        for pedido in pedidos_finais:
            if db.session.query(RelatorioVenda).filter_by(pedido_id=pedido.id).first() is None:
                db.session.add(RelatorioVenda(pedido=pedido, evento_em=pedido.criado_em))

        db.session.commit()

    print("Tabelas criadas ou já existentes: cliente, produto, pedido, formas_pagamento, contas_bancarias, vendas, estoque e relatorios.")


if __name__ == "__main__":
    create_database()
    create_tables()