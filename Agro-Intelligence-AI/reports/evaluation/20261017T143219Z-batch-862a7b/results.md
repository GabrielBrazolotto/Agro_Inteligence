# Avaliação automática — Etapa 2

Execução: 20261017T143219Z-batch-862a7b

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
    "passed": 1,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G02 | reused | 1.000 | 1.000 | ruptures:passed |

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

### G02

Quantas posições de estoque estão em ruptura observada, definida como disponível igual a zero?

Latência total: 3478.569 ms; falhas: []

Resposta:

Em **30 de setembro de 2026**, foram registradas **60 posições de estoque em ruptura observada** (definidas estritamente como quantidade disponível igual a zero), de um total de 3.000 posições monitoradas.

Detalhamento e contextualização das evidências:

* **Carteira em Ruptura:** Das 60 posições em ruptura observada, 41 apresentam carteira de pedidos pendentes, totalizando R$ 4.399.084,73. Este valor refere-se a pedidos represados e não deve ser interpretado como receita realizada ou perda financeira confirmada.
* **Diferenciação de Categorias:** A ruptura observada (disponível igual a zero) é uma categoria mutuamente exclusiva da *insuficiência com saldo positivo* (695 posições, nas quais existe estoque, porém em quantidade inferior à carteira).
* **Consolidação do Grupo Sinalizado:** O total de 755 pares sinalizados representa a união das rupturas observadas (60) com as insuficiências com saldo (695). O valor total deste grupo amplo não deve ser atribuído unicamente às rupturas.

Os dados refletem uma fotografia estática do abastecimento na data informada, sem aplicação de modelos de Machine Learning ou previsões estatísticas de perda.

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 5, "claims": 5, "protocol": "indexed_claim_evidence_v2"}, "answer_relevancy": {"status": "evaluated", "score": 1.0, "relevant": 6, "units": 6, "protocol": "indexed_answer_lines_v2"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Contar posições produto/centro com saldo zero; não confundir insuficiência com ruptura.; referências: ["sql:ruptures"]

Verificações independentes: [{"check": "ruptures", "status": "passed", "reference_rows": [{"valor": 60}], "missing_or_inaccurate_values": []}]

Ferramentas: [{"agent": "estoque", "tool": "duckdb_estoque_pedidos", "status": "ok"}, {"agent": "estoque", "tool": "gemini_analise", "status": "ok"}, {"agent": "orquestrador", "tool": "gemini_sintese", "status": "ok"}]

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
  }
]
```
