# Avaliação automática — Etapa 2

Execução: 20261017T130820Z

{
  "attempted_questions": 1,
  "answers_received": 1,
  "questions_evaluated": 0,
  "api_failed_questions": 1,
  "cost": null,
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
    "passed": 1,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G01 | degraded | not_executed | not_executed | revenue:passed |
| G02 | not_executed | not_executed | not_executed |  |
| G03 | not_executed | not_executed | not_executed |  |
| G04 | not_executed | not_executed | not_executed |  |
| G05 | not_executed | not_executed | not_executed |  |
| G06 | not_executed | not_executed | not_executed |  |
| G07 | not_executed | not_executed | not_executed |  |
| G08 | not_executed | not_executed | not_executed |  |
| G09 | not_executed | not_executed | not_executed |  |
| G10 | not_executed | not_executed | not_executed |  |
| G11 | not_executed | not_executed | not_executed |  |
| G12 | not_executed | not_executed | not_executed |  |
| G13 | not_executed | not_executed | not_executed |  |
| G14 | not_executed | not_executed | not_executed |  |
| G15 | not_executed | not_executed | not_executed |  |
| G16 | not_executed | not_executed | not_executed |  |
| G17 | not_executed | not_executed | not_executed |  |
| G18 | not_executed | not_executed | not_executed |  |

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

### G01

Qual é a receita líquida faturada total no período disponível? Informe o valor exato em reais.

Latência total: 36958.955 ms; falhas: [{"stage": "gemini_analise", "http_code": 429, "category": "api"}]

Resposta:

A receita líquida faturada total no período disponível (de **01/10/2025 a 30/09/2026**) é de **R$ 493.126.517,02**.

**Detalhes da apuração:**
* **Status considerado:** Apuração restrita a itens com status **faturada** (totalizando 5.772 pedidos e 14.431 linhas de venda).
* **Exclusões:** Conforme as diretrizes comerciais [politica_comercial.md, trecho 1], os valores em carteira pendente (R$ 155.146.363,54) e os pedidos cancelados (R$ 34.784.595,17) não compõem a receita realizada e foram excluídos do indicador.

*Nota: Todos os dados apresentados são 100% sintéticos e utilizados estritamente para fins acadêmicos.*

**Resposta com limitação:** uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "generation_rate_limit"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "generation_rate_limit"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Somar somente itens faturados, informar período e não adicionar carteira.; referências: ["sql:revenue"]

Verificações independentes: [{"check": "revenue", "status": "passed", "reference_rows": [{"valor": "493126517.02"}], "missing_or_inaccurate_values": []}]

Ferramentas: [{"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "failed", "category": "api", "http": 429, "reference": "7f247489f2af"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "ok"}]

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
        "distance": 0.3629607558250427
      },
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.36496657133102417
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.3672947287559509
      }
    ]
  }
]
```

### G02

Quantas posições de estoque estão em ruptura observada, definida como disponível igual a zero?

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Contar posições produto/centro com saldo zero; não confundir insuficiência com ruptura.; referências: ["sql:ruptures"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G03

Quantas posições de estoque estão acima do estoque máximo? Não some unidades diferentes.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Contar posições em excesso sem somar volumes KG/L/sacas.; referências: ["sql:excess"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G04

Como evoluiu o faturamento por mês nos 12 meses disponíveis? Liste os valores exatos de cada mês.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Usar faturadas agrupadas por mês, sem incluir pendentes/canceladas.; referências: ["sql:monthly"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G05

Quais regiões possuem maior faturamento e qual a margem regional consolidada de cada uma? Informe receita exata e margem percentual.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Ordenar receita; margem ponderada = 100*(receita-custo)/receita, somente faturadas.; referências: ["sql:regional"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G06

Qual é a margem comercial bruta total em reais sobre os itens faturados? Não confunda com lucro líquido.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Somar receita líquida menos custo faturado e esclarecer conceito.; referências: ["sql:margin"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G07

Pela política comercial, quem aprova um desconto de 7%? Cite o documento.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Gerente comercial; intervalo acima de 5% até 8%; citar política recuperada.; referências: ["data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G08

Qual é o desconto para pagamento à vista e pode ser acumulado com outros descontos?

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: 2% sem acumular com outros descontos; citar fonte.; referências: ["data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G09

A política comercial permite desconto de 9% se o gerente aprovar?

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Não: acima de 8% não permitido; não inventar exceção.; referências: ["data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G10

Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens? Informe a carteira em saldo zero com valor exato.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Dois agentes; distinguir saldo zero do grupo amplo; carteira não é perda nem receita realizada.; referências: ["sql:rupture_pending", "sql:ruptures"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G11

Qual é o valor exato da carteira pendente e por que não deve ser somada ao faturamento?

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Somar somente pendentes e evitar dupla contagem entre pedidos e itens.; referências: ["sql:pending", "data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G12

Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Executar scikit-learn com exatamente sete entradas; score não calibrado e limitações do domínio.; referências: ["models/backorder/metadata.json", "agro_ai/ml/schema.py"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G13

Preveja o risco de backorder com estoque=500; prazo=2; transito=100; previsao_3m=120; vendas_1m=20; vendas_3m=60; estoque_minimo=30

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Inferência real com sete atributos; não supor classe pelo estoque nem usar regras como ML.; referências: ["models/backorder/metadata.json", "agro_ai/ml/schema.py"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G14

Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15 e avalie o impacto comercial na carteira e nas margens.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Dois agentes e inferência real; não associar entrada a SKU nem converter score em probabilidade calibrada.; referências: ["models/backorder/metadata.json", "sql:pending"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G15

Compare excesso de estoque, faturamento e descontos; consulte a política comercial antes de recomendar uma ação.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Dois agentes compartilham pares; distinguir descontos sintéticos de política autorizada.; referências: ["sql:excess", "sql:revenue", "data/documents/politica_comercial.md#PC-001"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G16

Qual é o melhor?

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Pedir esclarecimento sobre produto, período e critério; não escolher produto por suposição.; referências: ["agro_ai/assistant.py#INSTRUCTIONS"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G17

Escreva um poema sobre viagens espaciais.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Explicar o escopo comercial de insumos e oferecer ajuda dentro do domínio; não inventar dados comerciais.; referências: ["agro_ai/assistant.py#INSTRUCTIONS"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```

### G18

Preveja o risco de ruptura do produto PRD-00001 sem que eu forneça outros atributos.

Latência total: None ms; falhas: []

Resposta:

(não recebida)

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "rate_limit_circuit_open"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "rate_limit_circuit_open"}

Comportamento esperado: Pedir as sete entradas; não deduzir demanda ou prazo de dados incompatíveis; não executar inferência.; referências: ["agro_ai/ml/schema.py#FEATURES"]

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```
