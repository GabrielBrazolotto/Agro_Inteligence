# Avaliação automática — Etapa 2

Execução: 20261018T125307Z-batch-436322

{
  "attempted_questions": 1,
  "answers_received": 1,
  "questions_evaluated": 0,
  "api_failed_questions": 0,
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
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G07 | ok | not_executed | not_executed |  |

## Análise e melhorias

- Perguntas com falha de API: 0; respostas recebidas: 1; perguntas avaliadas pelo juiz: 0.
- Falhas de API e avaliações não executadas não recebem zero nem entram na média.
- Conferir evidências e vereditos por caso no JSON; scores abaixo de 0,8 indicam revisão, não diagnóstico absoluto.
- Se houver 429, interromper a bateria e retomar após verificar limites; não ampliar concorrência.
- Valores SQL ausentes/incorretos exigem revisar formatação, roteamento e agregações; juiz LLM não substitui o oráculo.
- Casos ambíguos/fora do escopo podem revelar consultas desnecessárias: avaliar roteador de esclarecimento/recusa.
- Juiz e gerador compartilham família de modelo: validar amostra humana e considerar juiz independente.
- Não há estimativa de custo nem promessa de desempenho de ML com esta bateria sintética.

## Evidências por caso

### G07

Pela política comercial, quem aprova um desconto de 7%? Cite o documento.

Latência total: 39936.294 ms; falhas: []

Resposta:

De acordo com a política comercial vigente (período didático de setembro a dezembro de 2026), um desconto de 7% exige a aprovação do **gerente comercial** [politica_comercial.md, trecho 1]. 

Pelas regras estabelecidas no documento:
* Descontos de até 5% podem ser aprovados pelo vendedor para pedidos a partir de R$ 15.000,00;
* Descontos acima de 5% e até 8% exigem aprovação da gerência comercial;
* Descontos acima de 8% não são permitidos nesta política [politica_comercial.md, trecho 1].

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "pending"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "pending"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Gerente comercial; intervalo acima de 5% até 8%; citar política recuperada.; referências: ["data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: [{"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "ok"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "ok"}]

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
    "id": "e2",
    "origin": "comercial.documentos",
    "content": [
      {
        "text": "# Política comercial fictícia — Agro Intelligence AI\nDocumento PC-001. Vigência didática: setembro a dezembro de 2026.\n\nDesconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.\n\nPagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.\n\nTodos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.\n",
        "source": "politica_comercial.md",
        "chunk": 1,
        "distance": 0.26010000705718994
      },
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.36386334896087646
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.3810644745826721
      }
    ]
  }
]
```
