# Avaliação automática — Etapa 2

Execução: 20261017T142045Z-batch-d6b957

{
  "attempted_questions": 2,
  "answers_received": 2,
  "questions_evaluated": 2,
  "api_failed_questions": 0,
  "cost": null,
  "questions_with_any_metric": 2,
  "questions_fully_evaluated": 1,
  "questions_partially_evaluated": 1,
  "faithfulness": {
    "evaluated": 1,
    "mean": 1.0,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "answer_relevancy": {
    "evaluated": 2,
    "mean": 0.9,
    "below_threshold": 0,
    "threshold": 0.8
  },
  "deterministic": {
    "passed": 2,
    "failed": 0
  }
}

| Caso | Geração | Faithfulness | Answer Relevancy | SQL |
|---|---|---|---|---|
| G02 | ok | invalid_judgment | 1.000 | ruptures:passed |
| G03 | ok | 1.000 | 0.800 | excess:passed |

## Análise e melhorias

- Perguntas com falha de API: 0; respostas recebidas: 2; perguntas avaliadas pelo juiz: 2.
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

Latência total: 34050.21 ms; falhas: []

Resposta:

Em **30 de setembro de 2026**, foram registradas **60 posições de estoque em ruptura observada** (definidas estritamente como quantidade disponível igual a zero), de um total de 3.000 posições monitoradas.

Detalhamento e contextualização das evidências:

* **Carteira em Ruptura:** Das 60 posições em ruptura observada, 41 apresentam carteira de pedidos pendentes, totalizando R$ 4.399.084,73. Este valor refere-se a pedidos represados e não deve ser interpretado como receita realizada ou perda financeira confirmada.
* **Diferenciação de Categorias:** A ruptura observada (disponível igual a zero) é uma categoria mutuamente exclusiva da *insuficiência com saldo positivo* (695 posições, nas quais existe estoque, porém em quantidade inferior à carteira).
* **Consolidação do Grupo Sinalizado:** O total de 755 pares sinalizados representa a união das rupturas observadas (60) com as insuficiências com saldo (695). O valor total deste grupo amplo não deve ser atribuído unicamente às rupturas.

Os dados refletem uma fotografia estática do abastecimento na data informada, sem aplicação de modelos de Machine Learning ou previsões estatísticas de perda.

Avaliação: {"faithfulness": {"status": "invalid_judgment", "score": null, "reason": "invalid_quote"}, "answer_relevancy": {"status": "evaluated", "score": 1.0, "relevant": 6, "units": 6, "protocol": "indexed_answer_lines_v2"}}

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

### G03

Quantas posições de estoque estão acima do estoque máximo? Não some unidades diferentes.

Latência total: 47111.155 ms; falhas: []

Resposta:

Em **30/09/2026**, com base na fotografia consolidada do estoque (que abrange um total de 3.000 posições), existem **60 posições** classificadas em excesso (acima do estoque máximo).

**Pontos de atenção:**
* **Período consultado:** Fotografia de estoque em 30/09/2026.
* **Métrica:** O valor reportado refere-se estritamente à contagem de posições (pares produto/centro), sem realizar qualquer soma de quantidades físicas em unidades de medida distintas (como sacas ou toneladas).
* **Ausência de documentação:** Não há informações nos documentos fornecidos sobre os parâmetros ou regras operacionais específicas utilizadas para determinar a linha de corte do estoque máximo de cada item, constando apenas o total consolidado da base de dados.

Avaliação: {"faithfulness": {"status": "evaluated", "score": 1.0, "supported": 1, "claims": 1, "protocol": "claim_verdict_judge_v1"}, "answer_relevancy": {"status": "evaluated", "score": 0.8, "relevant": 4, "units": 5, "protocol": "indexed_answer_lines_v2"}}

Falhas operacionais: {"generation_failure": null, "evaluation_failure": null, "skip_reason": null}

Comportamento esperado: Contar posições em excesso sem somar volumes KG/L/sacas.; referências: ["sql:excess"]

Verificações independentes: [{"check": "excess", "status": "passed", "reference_rows": [{"valor": 60}], "missing_or_inaccurate_values": []}]

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
  }
]
```
