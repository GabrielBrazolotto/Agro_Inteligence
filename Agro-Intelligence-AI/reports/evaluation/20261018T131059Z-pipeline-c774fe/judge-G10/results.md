# Avaliação automática — Etapa 2

Execução: 20261018T131148Z-batch-51b705

{
  "attempted_questions": 1,
  "answers_received": 1,
  "questions_evaluated": 1,
  "api_failed_questions": 0,
  "cost": null,
  "questions_with_any_metric": 1,
  "questions_fully_evaluated": 1,
  "questions_partially_evaluated": 0,
  "faithfulness": {
    "evaluated": 1,
    "mean": 1.0,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "answer_relevancy": {
    "evaluated": 1,
    "mean": 0.9473684210526315,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "deterministic": {
    "passed": 1,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G10 | reused | 1.000 | 0.947 | rupture_pending:passed |

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

### G10

Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens? Informe a carteira em saldo zero com valor exato.

Latência total: 48989.316 ms; falhas: []

Resposta:

No período de 01/10/2025 a 30/09/2026 (com fotografia de estoque em 30/09/2026), foram analisadas as rupturas observadas (itens com disponível zero) que afetam os pedidos pendentes. Todos os dados são fictícios.

### Impacto Comercial e Carteira em Saldo Zero
* **Valor Exato da Carteira em Ruptura:** **R$ 4.399.084,73** (abrangendo 103 linhas de pedidos e 101 pedidos distintos, distribuídos em 41 pares produto-centro em ruptura com carteira).
* **Custo da Carteira:** R$ 3.506.069,23.
* **Impacto Comercial na Margem Bruta:** **R$ 893.015,50**, o que representa uma margem percentual teórica de **20,3%** retida na carteira pendente.

### Principais Rupturas que Afetam Pedidos Pendentes (Amostra de Prioridades)
As rupturas observadas (disponível zero) de maior valor na carteira pendente incluem:
* **PRD-00012** (CTR-004, tonelada): R$ 378.888,68 em carteira pendente;
* **PRD-00016** (CTR-002, tonelada): R$ 339.247,27;
* **PRD-00002** (CTR-006, tonelada): R$ 275.189,64;
* **PRD-00006** (CTR-003, tonelada): R$ 262.012,62;
* **PRD-00002** (CTR-005, tonelada): R$ 231.883,34;
* **PRD-00014** (CTR-012, tonelada): R$ 201.914,05;
* **PRD-00010** (CTR-015, tonelada): R$ 180.987,80;
* **PRD-00017** (CTR-006, KG): R$ 166.603,01;
* **PRD-00011** (CTR-001, KG): R$ 146.315,83;
* **PRD-00001** (CTR-001, KG): R$ 125.904,66.

Conforme estabelecido em nossa diretriz [politica_comercial.md, trecho 1], pedidos pendentes não constituem receita faturada e a carteira pendente não deve ser somada à receita realizada.

**Resposta com limitação:** uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 16, "claims": 16, "protocol": "indexed_claim_evidence_v2"}, "answer_relevancy": {"status": "evaluated", "score": 0.9473684210526315, "relevant": 18, "units": 19, "protocol": "indexed_answer_lines_v2"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Dois agentes; distinguir saldo zero do grupo amplo; carteira não é perda nem receita realizada.; referências: ["sql:rupture_pending", "sql:ruptures"]

Verificações independentes: [{"check": "rupture_pending", "status": "passed", "reference_rows": [{"valor": "4399084.73"}], "missing_or_inaccurate_values": []}]

Ferramentas: [{"agent": "estoque", "tool": "duckdb_estoque_pedidos", "status": "ok"}, {"agent": "estoque", "tool": "gemini_analise", "status": "failed", "category": "timeout", "http": null, "reference": "03a2191d3454"}, {"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "duckdb_impacto_pares", "status": "ok", "depends_on": "estoque.duckdb_estoque_pedidos"}, {"agent": "comercial", "tool": "duckdb_impacto_rupturas_total", "status": "ok", "depends_on": "estoque.duckdb_estoque_pedidos"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "ok"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "ok"}]

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
          "produto_id": 12,
          "centro_id": 4,
          "produto": "PRD-00012",
          "centro": "CTR-004",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 97,
          "carteira_valor": "378888.68"
        },
        {
          "produto_id": 16,
          "centro_id": 2,
          "produto": "PRD-00016",
          "centro": "CTR-002",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 96,
          "carteira_valor": "339247.27"
        },
        {
          "produto_id": 2,
          "centro_id": 6,
          "produto": "PRD-00002",
          "centro": "CTR-006",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 70,
          "carteira_valor": "275189.64"
        },
        {
          "produto_id": 6,
          "centro_id": 3,
          "produto": "PRD-00006",
          "centro": "CTR-003",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 94,
          "carteira_valor": "262012.62"
        },
        {
          "produto_id": 2,
          "centro_id": 5,
          "produto": "PRD-00002",
          "centro": "CTR-005",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 57,
          "carteira_valor": "231883.34"
        },
        {
          "produto_id": 14,
          "centro_id": 12,
          "produto": "PRD-00014",
          "centro": "CTR-012",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 41,
          "carteira_valor": "201914.05"
        },
        {
          "produto_id": 10,
          "centro_id": 15,
          "produto": "PRD-00010",
          "centro": "CTR-015",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 43,
          "carteira_valor": "180987.80"
        },
        {
          "produto_id": 17,
          "centro_id": 6,
          "produto": "PRD-00017",
          "centro": "CTR-006",
          "unidade": "KG",
          "disponivel": 0,
          "carteira_quantidade": 38360,
          "carteira_valor": "166603.01"
        },
        {
          "produto_id": 8,
          "centro_id": 8,
          "produto": "PRD-00008",
          "centro": "CTR-008",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 31,
          "carteira_valor": "150070.70"
        },
        {
          "produto_id": 18,
          "centro_id": 8,
          "produto": "PRD-00018",
          "centro": "CTR-008",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 53,
          "carteira_valor": "146376.94"
        },
        {
          "produto_id": 11,
          "centro_id": 1,
          "produto": "PRD-00011",
          "centro": "CTR-001",
          "unidade": "KG",
          "disponivel": 0,
          "carteira_quantidade": 31816,
          "carteira_valor": "146315.83"
        },
        {
          "produto_id": 16,
          "centro_id": 1,
          "produto": "PRD-00016",
          "centro": "CTR-001",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 41,
          "carteira_valor": "144517.20"
        },
        {
          "produto_id": 16,
          "centro_id": 3,
          "produto": "PRD-00016",
          "centro": "CTR-003",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 38,
          "carteira_valor": "136034.11"
        },
        {
          "produto_id": 1,
          "centro_id": 1,
          "produto": "PRD-00001",
          "centro": "CTR-001",
          "unidade": "KG",
          "disponivel": 0,
          "carteira_quantidade": 25560,
          "carteira_valor": "125904.66"
        },
        {
          "produto_id": 10,
          "centro_id": 14,
          "produto": "PRD-00010",
          "centro": "CTR-014",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 30,
          "carteira_valor": "120044.40"
        },
        {
          "produto_id": 14,
          "centro_id": 10,
          "produto": "PRD-00014",
          "centro": "CTR-010",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 24,
          "carteira_valor": "115767.38"
        },
        {
          "produto_id": 4,
          "centro_id": 11,
          "produto": "PRD-00004",
          "centro": "CTR-011",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 54,
          "carteira_valor": "115522.44"
        },
        {
          "produto_id": 4,
          "centro_id": 12,
          "produto": "PRD-00004",
          "centro": "CTR-012",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 50,
          "carteira_valor": "104552.45"
        },
        {
          "produto_id": 6,
          "centro_id": 2,
          "produto": "PRD-00006",
          "centro": "CTR-002",
          "unidade": "tonelada",
          "disponivel": 0,
          "carteira_quantidade": 35,
          "carteira_valor": "102186.49"
        },
        {
          "produto_id": 11,
          "centro_id": 3,
          "produto": "PRD-00011",
          "centro": "CTR-003",
          "unidade": "KG",
          "disponivel": 0,
          "carteira_quantidade": 21388,
          "carteira_valor": "101511.89"
        }
      ],
      "escopo_prioridades": "ruptura",
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
      "carteira_por_vencimento": [
        {
          "mes_vencimento": "2025-10",
          "pedidos": 3,
          "valor_pendente": "355618.39"
        },
        {
          "mes_vencimento": "2025-11",
          "pedidos": 79,
          "valor_pendente": "6197664.84"
        },
        {
          "mes_vencimento": "2025-12",
          "pedidos": 138,
          "valor_pendente": "11541416.05"
        },
        {
          "mes_vencimento": "2026-01",
          "pedidos": 181,
          "valor_pendente": "13042189.79"
        },
        {
          "mes_vencimento": "2026-02",
          "pedidos": 116,
          "valor_pendente": "9408354.34"
        },
        {
          "mes_vencimento": "2026-03",
          "pedidos": 75,
          "valor_pendente": "6321954.41"
        },
        {
          "mes_vencimento": "2026-04",
          "pedidos": 86,
          "valor_pendente": "7846921.01"
        },
        {
          "mes_vencimento": "2026-05",
          "pedidos": 86,
          "valor_pendente": "8724113.42"
        },
        {
          "mes_vencimento": "2026-06",
          "pedidos": 88,
          "valor_pendente": "7943327.79"
        },
        {
          "mes_vencimento": "2026-07",
          "pedidos": 99,
          "valor_pendente": "9360460.00"
        },
        {
          "mes_vencimento": "2026-08",
          "pedidos": 135,
          "valor_pendente": "11773447.39"
        },
        {
          "mes_vencimento": "2026-09",
          "pedidos": 168,
          "valor_pendente": "15047823.53"
        },
        {
          "mes_vencimento": "2026-10",
          "pedidos": 262,
          "valor_pendente": "19619103.47"
        },
        {
          "mes_vencimento": "2026-11",
          "pedidos": 217,
          "valor_pendente": "19763707.29"
        },
        {
          "mes_vencimento": "2026-12",
          "pedidos": 99,
          "valor_pendente": "8200261.82"
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
          "categoria": "Fertilizantes",
          "unidade": "tonelada",
          "linhas_pendentes": 46,
          "pedidos": 46,
          "carteira_pendente": "3005195.51",
          "margem_carteira": "650582.93"
        },
        {
          "categoria": "Fertilizantes",
          "unidade": "KG",
          "linhas_pendentes": 23,
          "pedidos": 23,
          "carteira_pendente": "540335.39",
          "margem_carteira": "85460.74"
        }
      ]
    }
  },
  {
    "id": "e4",
    "origin": "comercial.impacto_rupturas_total",
    "content": {
      "escopo": "todos os pares com disponível zero; não apenas os 20 prioritários",
      "totais": {
        "linhas_pendentes": 103,
        "pedidos_distintos": 101,
        "carteira_pendente": "4399084.73",
        "custo_carteira": "3506069.23",
        "margem_carteira": "893015.50",
        "margem_pct": 20.3
      },
      "natureza": "Valores da carteira, não faturamento, perda comprovada ou previsão ML."
    }
  },
  {
    "id": "e5",
    "origin": "comercial.documentos",
    "content": [
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.39267706871032715
      },
      {
        "text": "# Política comercial fictícia — Agro Intelligence AI\nDocumento PC-001. Vigência didática: setembro a dezembro de 2026.\n\nDesconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.\n\nPagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.\n\nTodos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.\n",
        "source": "politica_comercial.md",
        "chunk": 1,
        "distance": 0.39659643173217773
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.41168808937072754
      }
    ]
  }
]
```
