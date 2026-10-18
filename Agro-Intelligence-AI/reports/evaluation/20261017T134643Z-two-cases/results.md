# Avaliação automática — Etapa 2

Execução: 20261017T134643Z-two-cases

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
| G01 | reused | not_executed | not_executed | revenue:passed |
| G02 | not_executed | not_executed | not_executed |  |

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

Latência total: 2026.319 ms; falhas: []

Resposta:

A receita líquida faturada total no período disponível (de **01/10/2025 a 30/09/2026**) é de **R$ 493.126.517,02**.

**Detalhes da apuração:**
* **Status considerado:** Apuração restrita a itens com status **faturada** (totalizando 5.772 pedidos e 14.431 linhas de venda).
* **Exclusões:** Conforme as diretrizes comerciais [politica_comercial.md, trecho 1], os valores em carteira pendente (R$ 155.146.363,54) e os pedidos cancelados (R$ 34.784.595,17) não compõem a receita realizada e foram excluídos do indicador.

*Nota: Todos os dados apresentados são 100% sintéticos e utilizados estritamente para fins acadêmicos.*

**Resposta com limitação:** uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "api_error"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "api_error"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": {"status": "api_error", "error_category": "api", "http_code": 400}, "skip_reason": null}

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

Avaliação: {"faithfulness": {"status": "not_executed", "score": null, "reason": "api_failure_or_limit"}, "answer_relevancy": {"status": "not_executed", "score": null, "reason": "api_failure_or_limit"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": "api_failure_or_limit"}

Comportamento esperado: ; referências: []

Verificações independentes: []

Ferramentas: []

Evidências efetivamente recuperadas:

```json
[]
```
