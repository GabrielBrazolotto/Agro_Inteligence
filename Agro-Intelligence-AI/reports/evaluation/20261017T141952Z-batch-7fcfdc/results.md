# Avaliação automática — Etapa 2

Execução: 20261017T141952Z-batch-7fcfdc

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
| G12 | reused | 1.000 | 1.000 |  |

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

### G12

Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15

Latência total: 4047.396 ms; falhas: []

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

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 9, "claims": 9}, "answer_relevancy": {"status": "evaluated", "score": 1.0, "relevant": 11, "units": 11, "protocol": "indexed_answer_lines_v2"}}

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
