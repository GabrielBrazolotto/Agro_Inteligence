# Avaliação automática — Etapa 2

Execução: 20261017T134931Z-two-cases

{
  "attempted_questions": 2,
  "answers_received": 2,
  "questions_evaluated": 1,
  "api_failed_questions": 0,
  "cost": null,
  "questions_with_any_metric": 2,
  "questions_fully_evaluated": 1,
  "questions_partially_evaluated": 1,
  "faithfulness": {
    "evaluated": 2,
    "mean": 1.0,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "answer_relevancy": {
    "evaluated": 1,
    "mean": 0.6666666666666666,
    "below_threshold": 1,
    "threshold": 0.8
  },
  "deterministic": {
    "passed": 1,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G01 | reused | 1.000 | 0.667 | revenue:passed |
| G12 | ok | 1.000 | invalid_judgment |  |

## Análise e melhorias

- Perguntas com falha de API: 0; respostas recebidas: 2; perguntas avaliadas pelo juiz: 1.
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

Latência total: 2806.36 ms; falhas: []

Resposta:

A receita líquida faturada total no período disponível (de **01/10/2025 a 30/09/2026**) é de **R$ 493.126.517,02**.

**Detalhes da apuração:**
* **Status considerado:** Apuração restrita a itens com status **faturada** (totalizando 5.772 pedidos e 14.431 linhas de venda).
* **Exclusões:** Conforme as diretrizes comerciais [politica_comercial.md, trecho 1], os valores em carteira pendente (R$ 155.146.363,54) e os pedidos cancelados (R$ 34.784.595,17) não compõem a receita realizada e foram excluídos do indicador.

*Nota: Todos os dados apresentados são 100% sintéticos e utilizados estritamente para fins acadêmicos.*

**Resposta com limitação:** uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 3, "claims": 3}, "answer_relevancy": {"status": "evaluated", "score": 0.6666666666666666, "relevant": 2, "units": 3}, "judgment": {"claims": [{"quote": "A receita líquida faturada total no período disponível (de 01/10/2025 a 30/09/2026) é de R$ 493.126.517,02.", "supported": true, "evidence_ids": ["e1"], "reason": "O valor e o período coincidem com os dados fornecidos em 'totais' e 'resumo' na evidência e1."}, {"quote": "totalizando 5.772 pedidos e 14.431 linhas de venda", "supported": true, "evidence_ids": ["e1"], "reason": "Os números de pedidos e linhas de venda para o status 'faturada' estão corretos conforme a evidência e1."}, {"quote": "os valores em carteira pendente (R$ 155.146.363,54) e os pedidos cancelados (R$ 34.784.595,17) não compõem a receita realizada e foram excluídos do indicador.", "supported": true, "evidence_ids": ["e1", "e2"], "reason": "Os valores citados correspondem aos dados da evidência e1 e a exclusão está alinhada com a diretriz da política comercial na evidência e2."}], "relevance_units": [{"quote": "A receita líquida faturada total no período disponível (de 01/10/2025 a 30/09/2026) é de R$ 493.126.517,02.", "relevant": true, "reason": "Responde diretamente à pergunta sobre a receita líquida total."}, {"quote": "Detalhes da apuração: Status considerado: Apuração restrita a itens com status faturada (totalizando 5.772 pedidos e 14.431 linhas de venda). Exclusões: Conforme as diretrizes comerciais [politica_comercial.md, trecho 1], os valores em carteira pendente (R$ 155.146.363,54) e os pedidos cancelados (R$ 34.784.595,17) não compõem a receita realizada e foram excluídos do indicador.", "relevant": true, "reason": "Fornece contexto relevante sobre a composição do valor e critérios de exclusão."}, {"quote": "Resposta com limitação: uma análise de agente ficou indisponível. A síntese final utiliza as evidências disponíveis; a análise desse agente ficou incompleta. Consulte o registro de ferramentas.", "relevant": false, "reason": "Trata-se de metadados sobre o processo de geração da resposta, sem valor para a gestão comercial."}], "explanation": "A resposta responde corretamente à pergunta, fornecendo o valor exato da receita líquida faturada e o período correspondente, além de detalhar os critérios de exclusão de pedidos pendentes e cancelados, conforme solicitado pelas evidências."}, "quote_validation": "literal_or_markdown_whitespace_only", "usage": {"input": 1866, "output": 771, "total": 2637}, "cost": null, "judge_model": "gemini-3.1-flash-lite"}

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

### G12

Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15

Latência total: 14862.409 ms; falhas: []

Resposta:

**Previsão ML experimental: Risco sinalizado de backorder.**

Score da classe backorder: **0.9267**; limiar validado: **0.91**. O score não é uma probabilidade calibrada nem garantia de ruptura futura.

Atributos usados pelo modelo:

- `national_inv`: 10
- `lead_time`: 8
- `in_transit_qty`: 0
- `forecast_3_month`: 100
- `sales_1_month`: 20
- `sales_3_month`: 60
- `min_bank`: 15

Fonte: [dataset público de backorders](https://github.com/akhiilkasare/Back-Order-Prediction-iNeuron/tree/3bf0817ebb1a20e675ff02244660507e59f180f2). Inferência feita pelo modelo scikit-learn treinado; o Gemini não calcula esta previsão. Não validado para uma cooperativa agroindustrial brasileira; backorder é um proxy de indisponibilidade para atender pedidos, não um diagnóstico agronômico ou um alerta operacional certificado.

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 9, "claims": 9}, "answer_relevancy": {"status": "invalid_judgment", "score": null, "reason": "invalid_quote"}, "judgment": {"claims": [{"quote": "Score da classe backorder: 0.9267", "supported": true, "evidence_ids": ["e1"], "reason": "O valor corresponde ao score fornecido na evidência (0.9266898444319546 arredondado)."}, {"quote": "limiar validado: 0.91", "supported": true, "evidence_ids": ["e1"], "reason": "O valor corresponde ao threshold fornecido na evidência (0.9099999999999999 arredondado)."}, {"quote": "national_inv: 10", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature national_inv na evidência."}, {"quote": "lead_time: 8", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature lead_time na evidência."}, {"quote": "in_transit_qty: 0", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature in_transit_qty na evidência."}, {"quote": "forecast_3_month: 100", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature forecast_3_month na evidência."}, {"quote": "sales_1_month: 20", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature sales_1_month na evidência."}, {"quote": "sales_3_month: 60", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature sales_3_month na evidência."}, {"quote": "min_bank: 15", "supported": true, "evidence_ids": ["e1"], "reason": "O valor coincide com a feature min_bank na evidência."}], "relevance_units": [{"quote": "Previsão ML experimental: Risco sinalizado de backorder.", "relevant": true, "reason": "Responde diretamente à solicitação de previsão de risco."}, {"quote": "Score da classe backorder: 0.9267; limiar validado: 0.91.", "relevant": true, "reason": "Fornece os dados quantitativos que fundamentam a previsão."}, {"quote": "Atributos usados pelo modelo: ...", "relevant": true, "reason": "Confirma os parâmetros utilizados para a inferência."}, {"quote": "Não validado para uma cooperativa agroindustrial brasileira; backorder é um proxy de indisponibilidade para atender pedidos, não um diagnóstico agronômico ou um alerta operacional certificado.", "relevant": true, "reason": "Esclarece as limitações e o escopo da ferramenta, o que é relevante para a gestão comercial."}], "explanation": "A resposta utilizou corretamente os dados da evidência fornecida para realizar a inferência solicitada, mantendo a transparência sobre a natureza experimental do modelo e suas limitações de aplicação."}, "quote_validation": "literal_or_markdown_whitespace_only", "usage": {"input": 909, "output": 886, "total": 1795}, "cost": null, "judge_model": "gemini-3.1-flash-lite"}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Executar scikit-learn com exatamente sete entradas; score não calibrado e limitações do domínio.; referências: ["models/backorder/metadata.json", "agro_ai/ml/schema.py"]

Verificações independentes: []

Ferramentas: [{"agent": "estoque", "tool": "validacao_e_inferencia_ml_local", "status": "ok"}]

Evidências efetivamente recuperadas:

```json
[
  {
    "id": "e1",
    "origin": "ml.inference",
    "content": {
      "class": 1,
      "score": 0.9266898444319546,
      "threshold": 0.9099999999999999,
      "features": {
        "national_inv": 10.0,
        "lead_time": 8.0,
        "in_transit_qty": 0.0,
        "forecast_3_month": 100.0,
        "sales_1_month": 20.0,
        "sales_3_month": 60.0,
        "min_bank": 15.0
      },
      "source": "https://github.com/akhiilkasare/Back-Order-Prediction-iNeuron/tree/3bf0817ebb1a20e675ff02244660507e59f180f2",
      "calibrated": false,
      "outside_training_range": []
    }
  }
]
```
