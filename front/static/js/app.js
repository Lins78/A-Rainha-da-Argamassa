const formContainer = document.getElementById('formContainer');
const resultado = document.getElementById('resultado');
const tipoOperacao = document.getElementById('tipoOperacao');
const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');

const campoTemplates = {
  produto: [
    { name: 'nome', label: 'Nome do produto', type: 'text', placeholder: 'Argamassa' },
    { name: 'preco', label: 'Preço', type: 'number', step: '0.01', placeholder: '250.00' },
    { name: 'estoque', label: 'Estoque', type: 'number', placeholder: '20' }
  ],
  entrada_estoque: [
    { name: 'produto_id', label: 'ID do produto', type: 'number', placeholder: '1' },
    { name: 'fornecedor_id', label: 'ID do fornecedor', type: 'number', placeholder: '1' },
    { name: 'quantidade', label: 'Quantidade recebida', type: 'number', placeholder: '20' },
    { name: 'custo_unitario', label: 'Custo unitário', type: 'number', step: '0.01', placeholder: '18.50' },
    { name: 'origem', label: 'Fornecedor/origem', type: 'text', placeholder: 'Fornecedor' },
    { name: 'documento', label: 'Documento', type: 'text', placeholder: 'NF-e 123' },
    { name: 'observacao', label: 'Observação', type: 'text', placeholder: 'Reposição' }
  ],
  fornecedor: [
    { name: 'nome', label: 'Nome do fornecedor', type: 'text', placeholder: 'Fornecedor' },
    { name: 'documento', label: 'CNPJ ou CPF', type: 'text', placeholder: '12.345.678/0001-90' },
    { name: 'telefone', label: 'Telefone', type: 'text', placeholder: '(11) 3333-4444' },
    { name: 'email', label: 'E-mail', type: 'text', placeholder: 'compras@fornecedor.com' },
    { name: 'endereco', label: 'Endereço', type: 'text', placeholder: 'Rua e número' }
  ],
  inventario: [],
  cliente: [
    { name: 'nome', label: 'Nome do cliente', type: 'text', placeholder: 'Maria' },
    { name: 'telefone', label: 'Telefone', type: 'text', placeholder: '(11) 99999-9999' }
  ],
  conta_bancaria: [
    { name: 'banco', label: 'Banco', type: 'text', placeholder: 'Banco do Brasil' },
    { name: 'agencia', label: 'Agência', type: 'text', placeholder: '0001' },
    { name: 'numero', label: 'Número da conta', type: 'text', placeholder: '12345-6' },
    { name: 'tipo_conta', label: 'Tipo (corrente, poupanca ou pagamento)', type: 'text', placeholder: 'corrente' },
    { name: 'titular', label: 'Titular', type: 'text', placeholder: 'Empresa' },
    { name: 'documento', label: 'Documento', type: 'text', placeholder: 'CNPJ ou CPF' },
    { name: 'chave_pix', label: 'Chave Pix', type: 'text', placeholder: 'financeiro@empresa.com' }
  ],
  venda: [
    { name: 'cliente_id', label: 'ID do cliente', type: 'number', placeholder: '1' },
    { name: 'produto_id', label: 'ID do produto', type: 'number', placeholder: '1' },
    { name: 'quantidade', label: 'Quantidade', type: 'number', placeholder: '2' },
    { name: 'forma_pagamento_id', label: 'Forma de pagamento', type: 'number', placeholder: '1' },
    { name: 'conta_bancaria_id', label: 'Conta bancária de destino (opcional se houver uma ativa)', type: 'number', placeholder: '1' }
  ],
  pedido: [
    { name: 'cliente_id', label: 'ID do cliente', type: 'number', placeholder: '1' },
    { name: 'produto_id', label: 'ID do produto', type: 'number', placeholder: '1' },
    { name: 'quantidade', label: 'Quantidade', type: 'number', placeholder: '2' }
  ],
  efetivar: [
    { name: 'forma_pagamento_id', label: 'Forma de pagamento', type: 'number', placeholder: '1' },
    { name: 'conta_bancaria_id', label: 'Conta bancária de destino (opcional se houver uma ativa)', type: 'number', placeholder: '1' }
  ],
  cancelar: [
    { name: 'motivo', label: 'Motivo do cancelamento', type: 'text', placeholder: 'Cliente desistiu' }
  ],
  soma: [
    { name: 'valores', label: 'Valores separados por vírgula', type: 'text', placeholder: '10, 20, 30' }
  ],
  subtracao: [
    { name: 'valor1', label: 'Valor 1', type: 'number', step: '0.01', placeholder: '50' },
    { name: 'valor2', label: 'Valor 2', type: 'number', step: '0.01', placeholder: '20' }
  ],
  multiplicacao: [
    { name: 'valor1', label: 'Valor 1', type: 'number', step: '0.01', placeholder: '12' },
    { name: 'valor2', label: 'Valor 2', type: 'number', step: '0.01', placeholder: '3' }
  ],
  divisao: [
    { name: 'dividendo', label: 'Dividendo', type: 'number', step: '0.01', placeholder: '100' },
    { name: 'divisor', label: 'Divisor', type: 'number', step: '0.01', placeholder: '4' }
  ],
  desconto: [
    { name: 'preco', label: 'Preço', type: 'number', step: '0.01', placeholder: '100' },
    { name: 'percentual_desconto', label: 'Percentual de desconto', type: 'number', step: '0.01', placeholder: '10' }
  ],
  margem: [
    { name: 'custo', label: 'Custo', type: 'number', step: '0.01', placeholder: '80' },
    { name: 'margem_percentual', label: 'Margem percentual', type: 'number', step: '0.01', placeholder: '30' }
  ],
  media: [
    { name: 'produto_ids', label: 'IDs dos produtos (opcional)', type: 'text', placeholder: '1,2,3' }
  ]
};

function renderFields() {
  const operation = tipoOperacao.value;
  const fields = campoTemplates[operation] || [];
  formContainer.innerHTML = '';

  fields.forEach((field) => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <label for="${field.name}">${field.label}</label>
      <input id="${field.name}" type="${field.type}" name="${field.name}" step="${field.step || '1'}" placeholder="${field.placeholder || ''}" />
    `;
    formContainer.appendChild(wrapper);
  });

  if (operation === 'efetivar' || operation === 'cancelar') {
    const pedidoField = document.createElement('div');
    pedidoField.innerHTML = `
      <label for="pedido_id">ID do pedido</label>
      <input id="pedido_id" type="number" placeholder="1" />
    `;
    formContainer.appendChild(pedidoField);
  }
}

function buildPayload(operation) {
  const fields = campoTemplates[operation] || [];
  const payload = {};

  fields.forEach((field) => {
    const input = document.getElementById(field.name);
    if (!input) return;
    const value = input.value.trim();
    if (value === '') return;

    if (field.name === 'valores') {
      payload[field.name] = value.split(',').map((item) => Number(item.trim())).filter((n) => !Number.isNaN(n));
      return;
    }

    if (['cliente_id', 'produto_id', 'fornecedor_id', 'quantidade', 'forma_pagamento_id', 'conta_bancaria_id', 'estoque', 'preco', 'custo_unitario', 'valor1', 'valor2', 'dividendo', 'divisor', 'percentual_desconto', 'custo', 'margem_percentual'].includes(field.name)) {
      payload[field.name] = Number(value);
      return;
    }

    payload[field.name] = value;
  });

  const pedidoInput = document.getElementById('pedido_id');
  if ((operation === 'efetivar' || operation === 'cancelar') && pedidoInput && pedidoInput.value) {
    payload.pedido_id = Number(pedidoInput.value);
  }

  return payload;
}

function executar() {
  const operation = tipoOperacao.value;
  const apiKey = window.API_KEY || 'demo-api-key';
  const payload = buildPayload(operation);

  const urlMap = {
    produto: '/produtos',
    entrada_estoque: '/entradas-estoque',
    fornecedor: '/fornecedores',
    inventario: '/inventario',
    cliente: '/clientes',
    conta_bancaria: '/contas-bancarias',
    venda: '/venda',
    pedido: '/pedidos',
    efetivar: '/pedidos/' + (document.getElementById('pedido_id')?.value || 1) + '/efetivar',
    cancelar: '/pedidos/' + (document.getElementById('pedido_id')?.value || 1) + '/cancelar',
    soma: '/operacoes/soma',
    subtracao: '/operacoes/subtracao',
    multiplicacao: '/operacoes/multiplicacao',
    divisao: '/operacoes/divisao',
    desconto: '/operacoes/desconto',
    margem: '/operacoes/margem-lucro',
    media: '/operacoes/media-precos'
  };

  const methodMap = {
    produto: 'POST',
    entrada_estoque: 'POST',
    fornecedor: 'POST',
    inventario: 'GET',
    cliente: 'POST',
    conta_bancaria: 'POST',
    venda: 'POST',
    pedido: 'POST',
    efetivar: 'POST',
    cancelar: 'PATCH',
    soma: 'POST',
    subtracao: 'POST',
    multiplicacao: 'POST',
    divisao: 'POST',
    desconto: 'POST',
    margem: 'POST',
    media: 'GET'
  };

  const headers = {
    'X-API-Key': apiKey
  };

  if (operation === 'media' || operation === 'inventario') {
    const params = new URLSearchParams();
    if (operation === 'media' && payload.produto_ids) params.append('produto_ids', payload.produto_ids);
    const url = urlMap[operation] + (params.toString() ? `?${params.toString()}` : '');
    fetch(url, { headers })
      .then(async (response) => {
        const text = await response.text();
        try {
          return { ok: response.ok, data: JSON.parse(text) };
        } catch {
          return { ok: response.ok, data: text };
        }
      })
      .then(({ ok, data }) => {
        resultado.textContent = ok ? JSON.stringify(data, null, 2) : JSON.stringify(data, null, 2);
      })
      .catch((error) => {
        resultado.textContent = 'Erro: ' + error.message;
      });
    return;
  }

  const requestOptions = {
    method: methodMap[operation],
    headers: {
      ...headers,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  };

  fetch(urlMap[operation], requestOptions)
    .then(async (response) => {
      const text = await response.text();
      try {
        return { ok: response.ok, data: JSON.parse(text) };
      } catch {
        return { ok: response.ok, data: text };
      }
    })
    .then(({ ok, data }) => {
      resultado.textContent = ok ? JSON.stringify(data, null, 2) : JSON.stringify(data, null, 2);
    })
    .catch((error) => {
      resultado.textContent = 'Erro: ' + error.message;
    });
}

tipoOperacao.addEventListener('change', () => {
  renderFields();
  resultado.textContent = 'Resultado aparecerá aqui.';
});

submitBtn.addEventListener('click', executar);
resetBtn.addEventListener('click', () => {
  formContainer.innerHTML = '';
  resultado.textContent = 'Resultado aparecerá aqui.';
  renderFields();
});

renderFields();
