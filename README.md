# A Rainha da Argamassa

Aplicação Flask para cadastro de produtos, clientes, registro de vendas e operações matemáticas.

## Requisitos

- Python 3.11+
- PostgreSQL 11+
- `pip install -r requirements.txt`

## Configuração

Defina as variáveis de ambiente `DATABASE_URL`, `SECRET_KEY` e `API_KEY`:

```bash
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/revenda_argamassa"
export SECRET_KEY="gere-um-segredo-aleatorio"
export API_KEY="gere-uma-chave-de-api-aleatoria"
```

No Windows PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://usuario:senha@localhost:5432/revenda_argamassa"
$env:SECRET_KEY = "gere-um-segredo-aleatorio"
$env:API_KEY = "gere-uma-chave-de-api-aleatoria"
```

Em produção, as três variáveis são obrigatórias. Requisições protegidas devem enviar o cabeçalho `X-API-Key`.
Em desenvolvimento, sem `DATABASE_URL`, a aplicação usa SQLite local.

## Criar o banco PostgreSQL

Com o PostgreSQL em execução e um usuário com permissão para criar bancos, defina `DATABASE_URL` e execute o inicializador:

```powershell
$env:DATABASE_URL = "postgresql://usuario:senha@localhost:5432/revenda_argamassa"
python init_db.py
```

No Linux/macOS:

```bash
DATABASE_URL="postgresql://usuario:senha@localhost:5432/revenda_argamassa" python init_db.py
```

O comando cria `revenda_argamassa` se necessário e cria as tabelas `cliente`, `fornecedores`, `produto`, `inventario`, `pedido`, `formas_pagamento`, `contas_bancarias`, `entradas_estoque`, `vendas`, `estoque` e `relatorios`.

Para aplicar somente a alteração de contas bancárias em uma base já existente:

```powershell
$env:DATABASE_URL = "postgresql://usuario:senha@localhost:5432/revenda_argamassa"
python database/migrate_contas_bancarias.py
```
Pedidos possuem os status `aberto`, `efetivado` e `cancelado`. A tabela `vendas` guarda somente transações efetivadas e referencia o pedido de origem.
A tabela `estoque` registra cada saída vinculada à venda, incluindo quantidade, saldo anterior, saldo atual e data da movimentação.

## Executar a aplicação

```bash
python app.py
```

> Observação: O banco de dados não é criado automaticamente na inicialização.

Para produção, use Waitress atrás de HTTPS:

```bash
waitress-serve --listen=127.0.0.1:5000 wsgi:application
```

O módulo `app.py` também força `debug=False` quando executado diretamente.

## Endpoints principais

- `POST /produtos`
- `POST /clientes`
- `POST /contas-bancarias`
- `GET /contas-bancarias`
- `POST /entradas-estoque`
- `GET /entradas-estoque`
- `POST /fornecedores`
- `GET /fornecedores`
- `GET /inventario`
- `PATCH /inventario/<produto_id>`
- `POST /venda`
- `POST /pedidos` (cria pedido sem afetar o estoque)
- `POST /pedidos/<id>/efetivar`
- `PATCH /pedidos/<id>/cancelar`
- `GET /vendas/resumo?periodo=diario|semanal|mensal`
- `GET /relatorios/vendas?status=efetivada|cancelada`

O campo `forma_pagamento_id` de uma venda referencia `formas_pagamento`, e `conta_bancaria_id` referencia a conta que receberá o valor. Quando existe apenas uma conta ativa, ela é selecionada automaticamente; com várias contas ativas, informe o ID explicitamente. O inicializador cadastra Dinheiro, Pix, Cartão de crédito, Cartão de débito, Boleto bancário e Transferência bancária.
- `POST /operacoes/soma`
- `POST /operacoes/subtracao`
- `POST /operacoes/multiplicacao`
- `POST /operacoes/divisao`
- `POST /operacoes/desconto`
- `POST /operacoes/margem-lucro`
- `GET /operacoes/media-precos`
- `GET /health` (verificação pública de disponibilidade)

## Testes

```bash
pytest
```

## Recomendações operacionais e de segurança

- Use PostgreSQL com TLS e um usuário de banco com privilégios mínimos.
- Armazene segredos em um Secret Manager ou no cofre de variáveis do ambiente de execução.
- Faça backups criptografados e teste regularmente a restauração.
- Monitore logs, erros, latência, disponibilidade e falhas de banco; não grave tokens ou credenciais.
- Execute migrações versionadas antes de iniciar a aplicação após mudanças de esquema.
- Configure um proxy reverso com HTTPS, limite de requisições e firewall.
- Integre CI com testes, lint, análise de tipos e auditoria de dependências.
