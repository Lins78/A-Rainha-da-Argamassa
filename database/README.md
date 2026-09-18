# Banco de dados PostgreSQL

## Pré-requisitos
- PostgreSQL instalado e em execução
- Acesso com usuário que possa criar bancos e tabelas

## Criação do banco
No PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://usuario:senha@localhost:5432/revenda_argamassa"
python back/init_db.py
```

Ou, se preferir executar manualmente:

```sql
CREATE DATABASE revenda_argamassa;
```

Depois conecte-se ao banco e rode o script:

```bash
psql -d revenda_argamassa -f database/schema.sql
```

## Estrutura principal
- cliente
- produto
- pedido
- formas_pagamento
- vendas
- estoque
- relatorios

## Relacionamentos
- pedido -> cliente
- pedido -> produto
- vendas -> pedido
- vendas -> cliente
- vendas -> produto
- vendas -> formas_pagamento
- estoque -> produto
- estoque -> vendas
- relatorios -> pedido

## Observação
Esse schema é a base da Sprint 1 e deve ser usado como referência antes da implementação final do backend em produção.
