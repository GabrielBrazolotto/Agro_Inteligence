# Avaliação automática — Etapa 2

Execução: 20261018T144839Z-batch-ae229a

{
  "attempted_questions": 1,
  "answers_received": 1,
  "questions_evaluated": 1,
  "api_failed_questions": 0,
  "cost": null,
  "questions_with_any_metric": 1,
  "questions_fully_evaluated": 0,
  "questions_partially_evaluated": 1,
  "faithfulness": {
    "evaluated": 0,
    "mean": null,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "answer_relevancy": {
    "evaluated": 1,
    "mean": 1.0,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "deterministic": {
    "passed": 0,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G15 | reused | invalid_judgment | 1.000 |  |

## Análise e melhorias

- Perguntas com falha de API: 0; respostas recebidas: 1; perguntas avaliadas pelo juiz: 1.
- Falhas de API e avaliações não executadas não recebem zero nem entram na média.
- Conferir evidências e vereditos por caso no JSON; scores abaixo de 0,8 indicam revisão, não diagnóstico absoluto.
- Se houver 429, interromper a bateria e retomar após verificar limites; não ampliar concorrência.
- Valores SQL ausentes/incorretos exigem revisar formatação, roteamento e agregações; juiz LLM não substitui o oráculo.
- Casos ambíguos/fora do escopo podem revelar consultas desnecessárias: avaliar roteador de esclarecimento/recusa.
- Juiz e gerador compartilham família de modelo: validar amostra humana e considerar juiz independente.
- Não há estimativa de custo nem promessa de desempenho de ML com esta bateria sintética.

## Evidências por caso

### G15

Compare excesso de estoque, faturamento e descontos; consulte a política comercial antes de recomendar uma ação.

Latência total: 6102.622 ms; falhas: []

Resposta:

**Período Consultado**: Comercial de 01/10/2025 a 30/09/2026; Posição de estoque em 30/09/2026.

### Comparativo: Excesso, Faturamento e Descontos

1. **Faturamento Realizado**: A receita total de vendas faturadas no período foi de **R$ 493.126.517,02** (desconsiderando pedidos pendentes ou cancelados).
2. **Excesso de Estoque**: Identificaram-se **60 posições de excesso**. Por exemplo, os produtos PRD-00021 (com 5.000 KG nos centros CTR-001, CTR-002 e CTR-003) e PRD-00022 (com 5.000 toneladas nos centros CTR-004 e CTR-005) apresentam volumes muito superiores ao limite máximo estipulado de 1.000 unidades por centro.
3. **Práticas de Desconto**: No faturamento, o cenário sintético de "desconto elevado e margem negativa" acumulou **R$ 1.707.369,32** em receita faturada (62 linhas), resultando em prejuízo de R$ -208.264,67.

### Regras da Política Comercial

Conforme a regra oficial descrita em `[politica_comercial.md, trecho 1]`:
* **Até 5% de desconto**: Aprovado diretamente pelo vendedor para pedidos a partir de R$ 15.000,00.
* **Entre 5% e 8% de desconto**: Exige aprovação prévia do gerente comercial.
* **Acima de 8% de desconto**: Não é permitido sob nenhuma hipótese.
* **Pagamento à vista**: Concede 2% de desconto adicional, porém **não cumulativo** com outros descontos.

Os casos de margem negativa e descontos excessivos presentes na base de dados representam **cenários sintéticos de teste** e não políticas autorizadas pela empresa.

### Ação Recomendada

Para escoar os volumes em excesso (como os lotes de PRD-00021 e PRD-00022) sem comprometer a rentabilidade nem violar a governança:
1. **Campanha Promocional Direcionada**: Ativar a força de vendas para negociar os produtos em excesso oferecendo desconto regular de até 5% para pedidos qualificados (mínimo de R$ 15.000,00) `[politica_comercial.md, trecho 1]`.
2. **Aprovação Gerencial**: Caso necessário para fechar volumes maiores com clientes estratégicos, submeter propostas de até 8% de desconto à gerência comercial `[politica_comercial.md, trecho 1]`.
3. **Incentivo à Vista**: Estimular a modalidade de pagamento à vista com 2% de desconto para acelerar o caixa, sem acumular com outras deduções `[politica_comercial.md, trecho 1]`.
4. **Proibição de Margem Negativa**: Veta-se a concessão de descontos anômalos acima de 8% que gerem margens operacionais negativas.

**Resposta com limitação:** uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.

Avaliação: {"faithfulness": {"status": "invalid_judgment", "score": null, "reason": "invalid_evidence_reference", "protocol": "indexed_claim_evidence_v2"}, "answer_relevancy": {"status": "evaluated", "score": 1.0, "relevant": 19, "units": 19, "protocol": "indexed_answer_lines_v2"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Dois agentes compartilham pares; distinguir descontos sintéticos de política autorizada.; referências: ["sql:excess", "sql:revenue", "data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: [{"agent": "estoque", "tool": "duckdb_estoque_pedidos", "status": "ok"}, {"agent": "estoque", "tool": "gemini_analise", "status": "ok"}, {"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "duckdb_impacto_pares", "status": "ok", "depends_on": "estoque.duckdb_estoque_pedidos"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "failed", "category": "api", "http": 504, "reference": "3ca194e204fd"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "ok"}]

Evidências efetivamente recuperadas:

```json
[
  {
    "id": "e1",
    "origin": "estoque.abastecimento",
    "content": {
      "totais": {
        "data_estoque": "2026-09-30",
        "posicoes": 3000,
        "rupturas_observadas": 60,
        "excessos": 60,
        "pares_sinalizados": 755,
        "rupturas_com_carteira": 41,
        "carteira_em_ruptura": "4399084.73",
        "insuficiencias_com_saldo": 695,
        "carteira_em_insuficiencia_com_saldo": "69752075.66",
        "carteira_nos_pares_sinalizados": "74151160.39"
      },
      "prioridades_amostra": [
        {
          "produto_id": 736,
          "centro_id": 2,
          "produto": "PRD-00736",
          "centro": "CTR-002",
          "unidade": "saca_20KG",
          "disponivel": 371,
          "carteira_quantidade": 667,
          "carteira_valor": "574218.03"
        },
        {
          "produto_id": 626,
          "centro_id": 3,
          "produto": "PRD-00626",
          "centro": "CTR-003",
          "unidade": "saca_20KG",
          "disponivel": 349,
          "carteira_quantidade": 655,
          "carteira_valor": "543491.95"
        },
        {
          "produto_id": 616,
          "centro_id": 3,
          "produto": "PRD-00616",
          "centro": "CTR-003",
          "unidade": "saca_20KG",
          "disponivel": 418,
          "carteira_quantidade": 561,
          "carteira_valor": "523019.51"
        },
        {
          "produto_id": 416,
          "centro_id": 1,
          "produto": "PRD-00416",
          "centro": "CTR-001",
          "unidade": "saca_40KG",
          "disponivel": 288,
          "carteira_quantidade": 1465,
          "carteira_valor": "507889.78"
        },
        {
          "produto_id": 471,
          "centro_id": 2,
          "produto": "PRD-00471",
          "centro": "CTR-002",
          "unidade": "saca_40KG",
          "disponivel": 430,
          "carteira_quantidade": 1468,
          "carteira_valor": "505322.91"
        },
        {
          "produto_id": 616,
          "centro_id": 2,
          "produto": "PRD-00616",
          "centro": "CTR-002",
          "unidade": "saca_20KG",
          "disponivel": 426,
          "carteira_quantidade": 550,
          "carteira_valor": "501756.66"
        },
        {
          "produto_id": 601,
          "centro_id": 3,
          "produto": "PRD-00601",
          "centro": "CTR-003",
          "unidade": "saca_20KG",
          "disponivel": 241,
          "carteira_quantidade": 602,
          "carteira_valor": "489628.59"
        },
        {
          "produto_id": 487,
          "centro_id": 5,
          "produto": "PRD-00487",
          "centro": "CTR-005",
          "unidade": "saca_40KG",
          "disponivel": 415,
          "carteira_quantidade": 1126,
          "carteira_valor": "478818.77"
        },
        {
          "produto_id": 156,
          "centro_id": 2,
          "produto": "PRD-00156",
          "centro": "CTR-002",
          "unidade": "tonelada",
          "disponivel": 53,
          "carteira_quantidade": 84,
          "carteira_valor": "478081.98"
        },
        {
          "produto_id": 591,
          "centro_id": 1,
          "produto": "PRD-00591",
          "centro": "CTR-001",
          "unidade": "saca_40KG",
          "disponivel": 92,
          "carteira_quantidade": 1156,
          "carteira_valor": "472648.06"
        },
        {
          "produto_id": 676,
          "centro_id": 3,
          "produto": "PRD-00676",
          "centro": "CTR-003",
          "unidade": "saca_20KG",
          "disponivel": 224,
          "carteira_quantidade": 540,
          "carteira_valor": "465934.58"
        },
        {
          "produto_id": 496,
          "centro_id": 1,
          "produto": "PRD-00496",
          "centro": "CTR-001",
          "unidade": "saca_40KG",
          "disponivel": 143,
          "carteira_quantidade": 1245,
          "carteira_valor": "451552.29"
        },
        {
          "produto_id": 546,
          "centro_id": 1,
          "produto": "PRD-00546",
          "centro": "CTR-001",
          "unidade": "saca_40KG",
          "disponivel": 169,
          "carteira_quantidade": 1163,
          "carteira_valor": "441474.93"
        },
        {
          "produto_id": 631,
          "centro_id": 3,
          "produto": "PRD-00631",
          "centro": "CTR-003",
          "unidade": "saca_20KG",
          "disponivel": 58,
          "carteira_quantidade": 495,
          "carteira_valor": "434385.76"
        },
        {
          "produto_id": 421,
          "centro_id": 2,
          "produto": "PRD-00421",
          "centro": "CTR-002",
          "unidade": "saca_40KG",
          "disponivel": 253,
          "carteira_quantidade": 1173,
          "carteira_valor": "423499.08"
        },
        {
          "produto_id": 662,
          "centro_id": 4,
          "produto": "PRD-00662",
          "centro": "CTR-004",
          "unidade": "saca_20KG",
          "disponivel": 380,
          "carteira_quantidade": 543,
          "carteira_valor": "423308.60"
        },
        {
          "produto_id": 546,
          "centro_id": 2,
          "produto": "PRD-00546",
          "centro": "CTR-002",
          "unidade": "saca_40KG",
          "disponivel": 562,
          "carteira_quantidade": 1103,
          "carteira_valor": "421735.91"
        },
        {
          "produto_id": 486,
          "centro_id": 1,
          "produto": "PRD-00486",
          "centro": "CTR-001",
          "unidade": "saca_40KG",
          "disponivel": 142,
          "carteira_quantidade": 985,
          "carteira_valor": "406255.32"
        },
        {
          "produto_id": 781,
          "centro_id": 2,
          "produto": "PRD-00781",
          "centro": "CTR-002",
          "unidade": "saca_20KG",
          "disponivel": 112,
          "carteira_quantidade": 484,
          "carteira_valor": "401980.29"
        },
        {
          "produto_id": 552,
          "centro_id": 5,
          "produto": "PRD-00552",
          "centro": "CTR-005",
          "unidade": "saca_40KG",
          "disponivel": 372,
          "carteira_quantidade": 1032,
          "carteira_valor": "394597.56"
        }
      ],
      "escopo_prioridades": "sinalizados",
      "natureza": "Ruptura observada = disponível zero; insuficiência com saldo positivo = carteira maior que disponível. O grupo amplo sinalizados é a união, não sinônimo de ruptura. Categorias mutuamente exclusivas. por produto/centro e mesma unidade. Não é previsão estatística nem score ML. Estoque é fotografia independente; carteira não é perda estimada."
    }
  },
  {
    "id": "e2",
    "origin": "comercial.indicadores",
    "content": {
      "regra": "Dados 100% sintéticos. Receita somente de itens faturados; carteira somente pendente. Pedidos e linhas são visões da mesma operação: não somar entre si. Receita líquida = bruta - descontos; impostos/devoluções não simulados. Margem bruta comercial = receita líquida - custo, não lucro líquido. Rankings e amostras são limitados; não concluir ausência a partir deles. KG, L, toneladas, sacas de 40KG e de 20KG são unidades distintas.",
      "limite_por_consulta": 20,
      "contagens": {
        "regioes": 5,
        "centros": 15,
        "clientes": 5000,
        "produtos": 1000,
        "historico_precos": 12000,
        "pedidos": 8000,
        "vendas": 20000,
        "estoque": 3000
      },
      "totais": {
        "inicio": "2025-10-01",
        "fim": "2026-09-30",
        "receita_faturada": "493126517.02",
        "custo_faturado": "393103460.81",
        "margem_faturada": "100023056.21",
        "carteira_pendente": "155146363.54",
        "valor_cancelado": "34784595.17"
      },
      "resumo": [
        {
          "status": "cancelada",
          "linhas": 1008,
          "pedidos": 396,
          "valor": "34784595.17"
        },
        {
          "status": "faturada",
          "linhas": 14431,
          "pedidos": 5772,
          "valor": "493126517.02"
        },
        {
          "status": "pendente",
          "linhas": 4561,
          "pedidos": 1832,
          "valor": "155146363.54"
        }
      ],
      "estoque_resumo": [
        {
          "unidade": "KG",
          "pares_produto_centro": 300,
          "disponivel": 233446,
          "rupturas": 30,
          "excessos": 30,
          "valor_estoque": "888117.83"
        },
        {
          "unidade": "L",
          "pares_produto_centro": 1200,
          "disponivel": 425332,
          "rupturas": 0,
          "excessos": 0,
          "valor_estoque": "41312128.07"
        },
        {
          "unidade": "saca_20KG",
          "pares_produto_centro": 600,
          "disponivel": 208296,
          "rupturas": 0,
          "excessos": 0,
          "valor_estoque": "141845310.52"
        },
        {
          "unidade": "saca_40KG",
          "pares_produto_centro": 600,
          "disponivel": 218247,
          "rupturas": 0,
          "excessos": 0,
          "valor_estoque": "69955289.47"
        },
        {
          "unidade": "tonelada",
          "pares_produto_centro": 300,
          "disponivel": 233878,
          "rupturas": 30,
          "excessos": 30,
          "valor_estoque": "834991667.58"
        }
      ],
      "alertas_estoque": [
        {
          "produto": "PRD-00021",
          "centro": "CTR-001",
          "unidade": "KG",
          "disponivel": 5000,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "excesso"
        },
        {
          "produto": "PRD-00021",
          "centro": "CTR-002",
          "unidade": "KG",
          "disponivel": 5000,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "excesso"
        },
        {
          "produto": "PRD-00021",
          "centro": "CTR-003",
          "unidade": "KG",
          "disponivel": 5000,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "excesso"
        },
        {
          "produto": "PRD-00022",
          "centro": "CTR-004",
          "unidade": "tonelada",
          "disponivel": 5000,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "excesso"
        },
        {
          "produto": "PRD-00022",
          "centro": "CTR-005",
          "unidade": "tonelada",
          "disponivel": 5000,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "excesso"
        },
        {
          "produto": "PRD-00001",
          "centro": "CTR-001",
          "unidade": "KG",
          "disponivel": 0,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "ruptura"
        },
        {
          "produto": "PRD-00001",
          "centro": "CTR-002",
          "unidade": "KG",
          "disponivel": 0,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "ruptura"
        },
        {
          "produto": "PRD-00001",
          "centro": "CTR-003",
          "unidade": "KG",
          "disponivel": 0,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "ruptura"
        },
        {
          "produto": "PRD-00002",
          "centro": "CTR-004",
          "unidade": "tonelada",
          "disponivel": 0,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "ruptura"
        },
        {
          "produto": "PRD-00002",
          "centro": "CTR-005",
          "unidade": "tonelada",
          "disponivel": 0,
          "estoque_minimo": 40,
          "estoque_maximo": 1000,
          "cenario": "ruptura"
        }
      ],
      "cenarios_comerciais": [
        {
          "cenario": "desconto_elevado_margem_negativa",
          "status": "cancelada",
          "linhas": 7,
          "receita_liquida": "248264.37",
          "margem": "-30229.40"
        },
        {
          "cenario": "desconto_elevado_margem_negativa",
          "status": "faturada",
          "linhas": 62,
          "receita_liquida": "1707369.32",
          "margem": "-208264.67"
        },
        {
          "cenario": "desconto_elevado_margem_negativa",
          "status": "pendente",
          "linhas": 31,
          "receita_liquida": "864747.90",
          "margem": "-105537.22"
        },
        {
          "cenario": "margem_alta",
          "status": "cancelada",
          "linhas": 4,
          "receita_liquida": "202050.10",
          "margem": "80815.81"
        },
        {
          "cenario": "margem_alta",
          "status": "faturada",
          "linhas": 75,
          "receita_liquida": "3308758.84",
          "margem": "1323473.44"
        },
        {
          "cenario": "margem_alta",
          "status": "pendente",
          "linhas": 21,
          "receita_liquida": "529808.37",
          "margem": "211929.79"
        },
        {
          "cenario": "margem_comprimida",
          "status": "cancelada",
          "linhas": 8,
          "receita_liquida": "255015.36",
          "margem": "0.00"
        },
        {
          "cenario": "margem_comprimida",
          "status": "faturada",
          "linhas": 70,
          "receita_liquida": "1946446.37",
          "margem": "0.00"
        },
        {
          "cenario": "margem_comprimida",
          "status": "pendente",
          "linhas": 22,
          "receita_liquida": "834481.78",
          "margem": "0.00"
        },
        {
          "cenario": "normal",
          "status": "cancelada",
          "linhas": 989,
          "receita_liquida": "34079265.34",
          "margem": "7025912.59"
        },
        {
          "cenario": "normal",
          "status": "faturada",
          "linhas": 14224,
          "receita_liquida": "486163942.49",
          "margem": "98907847.44"
        },
        {
          "cenario": "normal",
          "status": "pendente",
          "linhas": 4487,
          "receita_liquida": "152917325.49",
          "margem": "31130185.42"
        }
      ]
    }
  },
  {
    "id": "e3",
    "origin": "comercial.impacto_compartilhado",
    "content": {
      "escopo": "somente os até 20 pares priorizados pelo agente de estoque; não é total global",
      "pares_consultados": 20,
      "por_familia": [
        {
          "categoria": "Sementes de soja",
          "unidade": "saca_40KG",
          "linhas_pendentes": 59,
          "pedidos": 55,
          "carteira_pendente": "4503794.61",
          "margem_carteira": "936377.43"
        },
        {
          "categoria": "Sementes de milho",
          "unidade": "saca_20KG",
          "linhas_pendentes": 50,
          "pedidos": 48,
          "carteira_pendente": "4357723.97",
          "margem_carteira": "823949.80"
        },
        {
          "categoria": "Fertilizantes",
          "unidade": "tonelada",
          "linhas_pendentes": 5,
          "pedidos": 5,
          "carteira_pendente": "478081.98",
          "margem_carteira": "104204.18"
        }
      ]
    }
  },
  {
    "id": "e4",
    "origin": "comercial.documentos",
    "content": [
      {
        "text": "# Política comercial fictícia — Agro Intelligence AI\nDocumento PC-001. Vigência didática: setembro a dezembro de 2026.\n\nDesconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.\n\nPagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.\n\nTodos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.\n",
        "source": "politica_comercial.md",
        "chunk": 1,
        "distance": 0.2886497378349304
      },
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.35884058475494385
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.3737322688102722
      }
    ]
  }
]
```
