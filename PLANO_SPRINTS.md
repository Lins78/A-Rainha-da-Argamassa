# Plano de Sprints — A Rainha da Argamassa

## Visão geral
Este plano organiza o desenvolvimento do projeto em etapas claras, priorizando primeiro a base de dados e o modelo de negócio, antes de avançar para frontend e deploy.

> Observação: o projeto ainda não possui conexão com PostgreSQL, nem banco, nem tabelas criadas. Por isso, a ordem correta é: banco → modelo → regras → API → frontend → produção.

---

## Sprint 1 — Base de dados e ambiente PostgreSQL
**Objetivo:** preparar a infraestrutura real do sistema.

### Entregas
- Definir PostgreSQL como banco padrão do projeto
- Configurar ambiente com variáveis de conexão
- Criar script de inicialização do banco
- Criar tabelas principais
- Validar relacionamento entre entidades

### Tarefas
1. Ajustar a configuração de conexão para PostgreSQL
2. Criar arquivo de ambiente `.env.example`
3. Definir `DATABASE_URL`, `SECRET_KEY` e `API_KEY`
4. Criar estrutura inicial: cliente, produto, pedido, venda, estoque, relatorios, formas_pagamento
5. Validar criação do banco e tabelas

### Critério de conclusão
- Banco PostgreSQL acessível
- Tabelas criadas corretamente
- Conexão funcionando sem erro

---

## Sprint 2 — Modelagem do domínio e regras de negócio
**Objetivo:** formalizar as regras que regem o sistema.

### Entregas
- Revisar entidades e relacionamentos
- Definir regras de pedido, venda e cancelamento
- Garantir integridade do estoque
- Construir relatório de vendas

### Tarefas
1. Finalizar modelagem de Cliente, Produto, Pedido, Venda e Estoque
2. Definir status de pedido: `aberto`, `efetivado`, `cancelado`
3. Garantir que o estoque só seja reduzido na efetivação
4. Garantir que o cancelamento não afetar vendas nem estoque
5. Criar registros iniciais de formas de pagamento

### Critério de conclusão
- Fluxo de negócio consistente
- Sem inconsistências entre estoque, venda e pedido
- Relatórios refletindo o correto estado do sistema

---

## Sprint 3 — API e endpoints essenciais
**Objetivo:** disponibilizar uma API funcional para o domínio de negócio.

### Entregas
- Endpoints básicos funcionando
- Validações de payload
- Tratamento de erros padronizado
- Segurança por API key

### Tarefas
1. Revisar rotas de clientes, produtos, pedidos e vendas
2. Confirmar fluxo de criação de pedido e efetivação
3. Validar erro de estoque insuficiente
4. Validar forma de pagamento inválida
5. Ajustar mensagens e status HTTP

### Critério de conclusão
- API operacional com dados reais
- Endpoints estáveis
- Respostas consistentes em JSON

---

## Sprint 4 — Testes automatizados e validação de regra de negócio
**Objetivo:** garantir que o sistema funcione sem regressões.

### Entregas
- Cobertura de testes para casos principais
- Testes de regressão para estoque e venda
- Validação de relatórios

### Tarefas
1. Expandir suíte de testes em [back/tests.py](back/tests.py)
2. Cobrir fluxo de criação de cliente e produto
3. Cobrir venda com estoque suficiente
4. Cobrir venda sem estoque
5. Cobrir cancelamento de pedido
6. Cobrir relatório de vendas efetivadas e canceladas
7. Rodar pytest completo

### Critério de conclusão
- Todos os testes aprovados
- Fluxos essenciais cobertos
- Redução de regressões

---

## Sprint 5 — Frontend e experiência do usuário
**Objetivo:** permitir que o usuário opere o sistema sem depender diretamente da API.

### Entregas
- Cadastro de clientes
- Cadastro de produtos
- Registro de venda
- Consulta de pedidos
- Visualização de relatórios

### Tarefas
1. Ajustar HTML e CSS da interface principal
2. Integrar front-end com a API Flask
3. Implementar formulário de cadastro de cliente e produto
4. Implementar fluxo de venda e cancelamento
5. Exibir resumo financeiro e relatórios

### Critério de conclusão
- Usuário consegue operar o sistema pela interface
- Fluxos principais acessíveis sem uso manual de API

---

## Sprint 6 — Segurança, deploy e produção
**Objetivo:** preparar o projeto para uso real e profissional.

### Entregas
- Configuração de ambiente produtivo
- Segurança reforçada
- Documentação final
- Estrutura pronta para deploy

### Tarefas
1. Revisar secrets e variáveis de ambiente
2. Garantir uso de PostgreSQL em produção
3. Ajustar fallback de desenvolvimento
4. Documentar passos de execução
5. Preparar deploy em servidor ou container

### Critério de conclusão
- Projeto pronto para ambiente real com segurança adequada
- Execução em produção documentada

---

## Ordem recomendada de execução
1. PostgreSQL
2. Schema e tabelas
3. Modelagem de negócio
4. API
5. Testes
6. Frontend
7. Produção

---

## Metas de entrega por sprint
- Sprint 1: banco funcionando
- Sprint 2: regras do negócio definidas
- Sprint 3: API estabilizada
- Sprint 4: testes validando negócio
- Sprint 5: interface operável
- Sprint 6: projeto pronto para produção

---

## Observação final
A maior prioridade agora é construir a base que ainda falta: conexão com PostgreSQL, criação do banco e definição real das relações. Sem essa base, o restante do sistema corre risco de ser montado sobre uma estrutura instável.

---

## Como publicar isto no GitHub
Se quiser publicar esse plano no GitHub, você pode usar os comandos abaixo no terminal local:

```bash
git add PLANO_SPRINTS.md
git commit -m "Adicionar plano de sprints do projeto"
git branch -M main
git remote add origin <URL_DO_SEU_REPOSITORIO_GITHUB>
git push -u origin main
```

Se preferir, também pode renomear esse arquivo para algo mais apropriado como:
- `ROADMAP.md`
- `docs/PLANO_SPRINTS.md`
- `Sprints.md`

---

## Próximo passo recomendado
A próxima etapa ideal é começar pela Sprint 1 e montar a base real do banco PostgreSQL, incluindo schema e relacionamentos, antes de continuar com o frontend e o deploy.
