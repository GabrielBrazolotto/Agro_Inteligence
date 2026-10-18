# Avaliação consolidada — Etapa 2

Atualizado em 18/10/2026 a partir do estado atual do cache validado. Inclui os resultados da execução `20261018T131059Z-pipeline-c774fe` e a resposta de G11 já disponível no cache.

| Caso | Status atual | Faithfulness | Answer Relevancy |
|---|---|---|---|
| G01 | evaluated | 1.000 | 0.667 |
| G02 | evaluated | 1.000 | 1.000 |
| G03 | evaluated | 1.000 | 0.800 |
| G04 | evaluated | 1.000 | 0.318 |
| G05 | evaluated | 1.000 | 1.000 |
| G06 | partially_evaluated | invalid_judgment | 1.000 |
| G07 | evaluated | 1.000 | 1.000 |
| G08 | evaluated | 1.000 | 1.000 |
| G09 | evaluated | 1.000 | 1.000 |
| G10 | evaluated | 1.000 | 0.947 |
| G11 | response_available | not_executed | not_executed |
| G12 | evaluated | 1.000 | 1.000 |
| G13 | not_executed | not_executed | not_executed |
| G14 | not_executed | not_executed | not_executed |
| G15 | not_executed | not_executed | not_executed |
| G16 | not_executed | not_executed | not_executed |
| G17 | not_executed | not_executed | not_executed |
| G18 | not_executed | not_executed | not_executed |

**Situação:** 10 casos completos; G06 parcialmente avaliado; G11 com resposta salva aguardando julgamento; seis casos não executados.

- G04: série mensal completa, Faithfulness 1,000 e Relevancy 0,318. Documentos e avisos adicionais prejudicaram a relevância.
- G06: Relevancy 1,000; Faithfulness sem nota, pois o veredito foi rejeitado por `invalid_evidence_reference`.
- G10: avaliação concluída; o aviso de limitação da análise de estoque permanece na resposta armazenada.

Valores arredondados a três casas decimais apenas para exibição. Julgamentos inválidos e métricas não executadas não recebem zero.

Esta atualização não executou avaliações nem chamadas à API. Os relatórios das execuções, cache e métricas foram preservados. A versão anterior deste documento está em `consolidated.before-update.md`. O JSON original desta pasta permanece como registro histórico da validação local inicial.
