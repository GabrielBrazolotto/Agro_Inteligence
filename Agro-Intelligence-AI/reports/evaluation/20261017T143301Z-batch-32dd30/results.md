# Avaliação automática — Etapa 2

Execução: 20261017T143301Z-batch-32dd30

{
  "attempted_questions": 1,
  "answers_received": 1,
  "questions_evaluated": 0,
  "api_failed_questions": 1,
  "cost": null,
  "questions_with_any_metric": 0,
  "questions_fully_evaluated": 0,
  "questions_partially_evaluated": 0,
  "faithfulness": {
    "evaluated": 0,
    "mean": null,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "answer_relevancy": {
    "evaluated": 0,
    "mean": null,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "deterministic": {
    "passed": 0,
    "failed": 1
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G04 | fallback | not_executed | not_executed | monthly:failed |
| G05 | not_executed | not_executed | not_executed |  |

## Análise e melhorias

- Perguntas com falha de API: 1; respostas recebidas: 1; perguntas avaliadas pelo juiz: 0.
- Falhas de API e avaliações não executadas não recebem zero nem entram na média.
- Conferir evidências e vereditos por caso no JSON; scores abaixo de 0,8 indicam revisão, não diagnóstico absoluto.
- Se houver 429, interromper a bateria e retomar após verificar limites; não ampliar concorrência.
- Valores SQL ausentes/incorretos exigem revisar formatação, roteamento e agregações; juiz LLM não substitui o oráculo.
- Casos ambíguos/fora do escopo podem revelar consultas desnecessárias: avaliar roteador de esclarecimento/recusa.
- Juiz e gerador compartilham família de modelo: validar amostra humana e considerar juiz independente.
- Não há estimativa de custo nem promessa de desempenho de ML com esta bateria sintética.

## Evidências por caso

### G04

Como evoluiu o faturamento por mês nos 12 meses disponíveis? Liste uma linha por mês no formato YYYY-MM com o valor exato.

Latência total: 47468.479 ms; falhas: [{"stage": "gemini_analise", "category": "timeout", "http_code": null}, {"stage": "gemini_sintese", "category": "daily_limit", "http_code": 429}]

Resposta:

**Resumo factual das ferramentas — sem síntese do Gemini.**

**Resposta incompleta:** a síntese do Gemini ficou indisponível. Este resumo contém somente os resultados disponíveis das ferramentas.

Período 2025-10-01 a 2026-09-30: faturamento R$ 493.126.517,02; carteira pendente R$ 155.146.363,54; margem faturada R$ 100.023.056,21.

Trecho consultado [politica_comercial.md, trecho 1]:

> # Política comercial fictícia — Agro Intelligence AI
> Documento PC-001. Vigência didática: setembro a dezembro de 2026.
> 
> Desconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.
> 
> Pagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.
> 
> Todos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.
> 

Trecho consultado [logistica_atendimento.md, trecho 1]:

> # Entrega e atendimento fictícios
> Documento LOG-001. Vigência didática: setembro a dezembro de 2026.
> 
> Atendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.
> 
> Frete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.
> 
> Todas as condições são simulações acadêmicas e não representam uma empresa real.
> 

Trecho consultado [catalogo_comercial.md, trecho 1]:

> # Catálogo comercial fictício
> Documento CAT-001. Vigência didática: setembro a dezembro de 2026.
> 
> Fertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.
> 
> Os produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.
> 

Há consultas indisponíveis; veja o registro de ferramentas. Não foi inventado resultado para elas.

Dados comerciais sintéticos. Regras de disponibilidade, políticas e score estatístico são evidências distintas.

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "pending"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "pending"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Usar faturadas agrupadas por mês, sem incluir pendentes/canceladas.; referências: ["sql:monthly"]

Verificações independentes: [{"check": "monthly", "status": "failed", "reference_rows": [{"mes": "2025-10", "valor": "69100257.04"}, {"mes": "2025-11", "valor": "47569449.23"}, {"mes": "2025-12", "valor": "22958227.98"}, {"mes": "2026-01", "valor": "20195392.48"}, {"mes": "2026-02", "valor": "24733899.94"}, {"mes": "2026-03", "valor": "21990732.75"}, {"mes": "2026-04", "valor": "19900242.28"}, {"mes": "2026-05", "valor": "18898851.47"}, {"mes": "2026-06", "valor": "31224307.20"}, {"mes": "2026-07", "valor": "49589766.87"}, {"mes": "2026-08", "valor": "84051605.74"}, {"mes": "2026-09", "valor": "82913784.04"}], "missing_or_inaccurate_values": [{"field": "valor", "expected": "69100257.04", "group": "2025-10"}, {"field": "valor", "expected": "47569449.23", "group": "2025-11"}, {"field": "valor", "expected": "22958227.98", "group": "2025-12"}, {"field": "valor", "expected": "20195392.48", "group": "2026-01"}, {"field": "valor", "expected": "24733899.94", "group": "2026-02"}, {"field": "valor", "expected": "21990732.75", "group": "2026-03"}, {"field": "valor", "expected": "19900242.28", "group": "2026-04"}, {"field": "valor", "expected": "18898851.47", "group": "2026-05"}, {"field": "valor", "expected": "31224307.20", "group": "2026-06"}, {"field": "valor", "expected": "49589766.87", "group": "2026-07"}, {"field": "valor", "expected": "84051605.74", "group": "2026-08"}, {"field": "valor", "expected": "82913784.04", "group": "2026-09"}]}]

Ferramentas: [{"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "failed", "category": "timeout", "http": null, "reference": "acde0309a51c"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "failed", "category": "daily_limit", "http": 429, "reference": "b77b7adeebec"}]

Evidências efetivamente recuperadas:

```json
[
  {
    "id": "e1",
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
      "mensal": [
        {
          "mes": "2025-10",
          "receita_faturada": "69100257.04",
          "carteira_pendente": "19312146.84"
        },
        {
          "mes": "2025-11",
          "receita_faturada": "47569449.23",
          "carteira_pendente": "14718965.52"
        },
        {
          "mes": "2025-12",
          "receita_faturada": "22958227.98",
          "carteira_pendente": "6899802.23"
        },
        {
          "mes": "2026-01",
          "receita_faturada": "20195392.48",
          "carteira_pendente": "6190956.60"
        },
        {
          "mes": "2026-02",
          "receita_faturada": "24733899.94",
          "carteira_pendente": "7341237.46"
        },
        {
          "mes": "2026-03",
          "receita_faturada": "21990732.75",
          "carteira_pendente": "9406211.94"
        },
        {
          "mes": "2026-04",
          "receita_faturada": "19900242.28",
          "carteira_pendente": "7607415.97"
        },
        {
          "mes": "2026-05",
          "receita_faturada": "18898851.47",
          "carteira_pendente": "5836759.65"
        },
        {
          "mes": "2026-06",
          "receita_faturada": "31224307.20",
          "carteira_pendente": "11496612.31"
        },
        {
          "mes": "2026-07",
          "receita_faturada": "49589766.87",
          "carteira_pendente": "12604227.39"
        },
        {
          "mes": "2026-08",
          "receita_faturada": "84051605.74",
          "carteira_pendente": "25960661.80"
        },
        {
          "mes": "2026-09",
          "receita_faturada": "82913784.04",
          "carteira_pendente": "27771365.83"
        }
      ]
    }
  },
  {
    "id": "e2",
    "origin": "comercial.documentos",
    "content": [
      {
        "text": "# Política comercial fictícia — Agro Intelligence AI\nDocumento PC-001. Vigência didática: setembro a dezembro de 2026.\n\nDesconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.\n\nPagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.\n\nTodos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.\n",
        "source": "politica_comercial.md",
        "chunk": 1,
        "distance": 0.3896902799606323
      },
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.40149396657943726
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.40946877002716064
      }
    ]
  }
]
```

### G05

Quais regiões possuem maior faturamento e qual a margem regional consolidada de cada uma? Liste uma linha por região com nome, receita exata e margem percentual.

Latência total: 0.018 ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "api_failure_or_limit"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "api_failure_or_limit"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "api_failure_or_limit"}

Comportamento esperado: Ordenar receita; margem ponderada = 100*(receita-custo)/receita, somente faturadas.; referências: ["sql:regional"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```
