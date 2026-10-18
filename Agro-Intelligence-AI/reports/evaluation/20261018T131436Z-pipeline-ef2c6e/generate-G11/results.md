# Avaliação automática — Etapa 2

Execução: 20261018T131437Z-batch-70249c

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
    "passed": 1,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G11 | fallback | not_executed | not_executed | pending:passed |

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

### G11

Qual é o valor exato da carteira pendente e por que não deve ser somada ao faturamento?

Latência total: 50503.886 ms; falhas: [{"stage": "gemini_sintese", "category": "api", "http_code": 503}]

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

Comportamento esperado: Somar somente pendentes e evitar dupla contagem entre pedidos e itens.; referências: ["sql:pending", "data/documents/politica_comercial.md#PC-001"]

Verificações independentes: [{"check": "pending", "status": "passed", "reference_rows": [{"valor": "155146363.54"}], "missing_or_inaccurate_values": []}]

Ferramentas: [{"agent": "comercial", "tool": "duckdb_comercial", "status": "ok"}, {"agent": "comercial", "tool": "chroma_rag_comercial", "status": "ok"}, {"agent": "comercial", "tool": "gemini_analise", "status": "ok"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "failed", "category": "api", "http": 503, "reference": "3a09ef3f4b00"}]

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
    "id": "e2",
    "origin": "comercial.documentos",
    "content": [
      {
        "text": "# Política comercial fictícia — Agro Intelligence AI\nDocumento PC-001. Vigência didática: setembro a dezembro de 2026.\n\nDesconto de até 5% sobre o preço de lista pode ser aprovado pelo vendedor em pedidos a partir de R$ 15.000. Descontos acima de 5% e até 8% exigem aprovação do gerente comercial. Acima de 8% não são permitidos nesta política.\n\nPagamento padrão: 30 dias após o faturamento, sujeito à análise de crédito. Pagamento à vista permite desconto de 2%, sem acumular com outros descontos. Pedidos pendentes não constituem receita faturada. Pedidos cancelados devem ser excluídos dos indicadores de vendas realizadas.\n\nTodos os nomes, valores e condições são fictícios para a disciplina AI Factory da PUCPR.\n",
        "source": "politica_comercial.md",
        "chunk": 1,
        "distance": 0.4450308084487915
      },
      {
        "text": "# Entrega e atendimento fictícios\nDocumento LOG-001. Vigência didática: setembro a dezembro de 2026.\n\nAtendimento comercial de segunda a sexta-feira, das 8h às 18h, horário de Brasília. Entregas para Castro, Ponta Grossa e Guarapuava, no Paraná, têm prazo estimado de 3 a 5 dias úteis após aprovação de crédito e confirmação do pedido.\n\nFrete gratuito para pedidos a partir de R$ 20.000 nas três cidades atendidas. Abaixo desse valor, o frete é cotado separadamente. Solicitações de devolução por avaria devem ser registradas em até 7 dias corridos após o recebimento, com fotos e número do pedido, para análise da equipe.\n\nTodas as condições são simulações acadêmicas e não representam uma empresa real.\n",
        "source": "logistica_atendimento.md",
        "chunk": 1,
        "distance": 0.45732182264328003
      },
      {
        "text": "# Catálogo comercial fictício\nDocumento CAT-001. Vigência didática: setembro a dezembro de 2026.\n\nFertilizante NPK 10-10-10: saca de 50 kg, preço de lista de R$ 180,00. Semente de soja Aurora: saca de 40 kg, preço de lista de R$ 320,00. Condicionador de solo Terra Viva: litro, preço de lista de R$ 45,00.\n\nOs produtos e suas marcas são fictícios. A disponibilidade de estoque deve ser confirmada com a equipe comercial; este catálogo não informa estoque. O material não constitui recomendação agronômica, indicação de dose ou garantia de produtividade.\n",
        "source": "catalogo_comercial.md",
        "chunk": 1,
        "distance": 0.45813989639282227
      }
    ]
  }
]
```
