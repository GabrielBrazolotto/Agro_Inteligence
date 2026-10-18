# Evidência técnica complementar — G01 a G15

Consolidação offline em 2026-10-18T12:19:09.634311-03:00. Novas chamadas à API: zero.
Validação: 15 casos, 30 métricas com status evaluated e correspondência com os relatórios originais.

| ID | Pergunta original | Categoria | Faithfulness | Answer Relevancy | Determinístico DuckDB | Observações |
|---|---|---|---:|---:|---|---|
| G01 | Qual é a receita líquida faturada total no período disponível? Informe o valor exato em reais. | faturamento | 1.000000 | 0.666667 | revenue: passed | Receita exata; juiz penalizou aviso operacional (2/3 relevantes). |
| G02 | Quantas posições de estoque estão em ruptura observada, definida como disponível igual a zero? | estoque | 1.000000 | 1.000000 | ruptures: passed | 60 posições com disponível zero; separadas da insuficiência com saldo. |
| G03 | Quantas posições de estoque estão acima do estoque máximo? Não some unidades diferentes. | estoque | 1.000000 | 0.800000 | excess: passed | 60 posições em excesso. Relevancy igual a 0,8, não abaixo. |
| G04 | Como evoluiu o faturamento por mês nos 12 meses disponíveis? Liste uma linha por mês no formato YYYY-MM com o valor exato. | faturamento | 1.000000 | 0.318182 | monthly: passed | Fallback corrigido contém 12 meses; documentos adicionais reduziram Relevancy (14/44). Zero histórico preservado. |
| G05 | Quais regiões possuem maior faturamento e qual a margem regional consolidada de cada uma? Liste uma linha por região com nome, receita exata e margem percentual. | regional_margens | 1.000000 | 1.000000 | regional: passed | Margem regional ponderada por receita, somente itens faturados. |
| G06 | Qual é a margem comercial bruta total em reais sobre os itens faturados? Não confunda com lucro líquido. | regional_margens | 1.000000 | 1.000000 | margin: passed | Novo julgamento válido após inconsistência anterior; Relevancy anterior preservada. |
| G07 | Pela política comercial, quem aprova um desconto de 7%? Cite o documento. | rag_politica | 1.000000 | 1.000000 | Não aplicável | Desconto de 7% exige gerente comercial, conforme documento recuperado. |
| G08 | Qual é o desconto para pagamento à vista e pode ser acumulado com outros descontos? | rag_politica | 1.000000 | 1.000000 | Não aplicável | Pagamento à vista: 2%, sem acumular outros descontos. |
| G09 | A política comercial permite desconto de 9% se o gerente aprovar? | rag_politica | 1.000000 | 1.000000 | Não aplicável | 9% não autorizado pela política, mesmo com aprovação gerencial. |
| G10 | Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens? Informe a carteira em saldo zero com valor exato. | pedidos_rupturas_composta | 1.000000 | 0.947368 | rupture_pending: passed | Síntese concluída com aviso do timeout de análise de estoque; carteira em ruptura conferida. |
| G11 | Qual é o valor exato da carteira pendente e por que não deve ser somada ao faturamento? | pedidos_pendentes | 1.000000 | 0.060606 | pending: passed | Fallback após HTTP 503; carteira correta, mas só 2/33 linhas relevantes. |
| G12 | Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15 | ml_valido | 1.000000 | 1.000000 | Não aplicável | Inferência scikit-learn local com sete entradas explícitas; score não calibrado. |
| G13 | Preveja o risco de backorder com estoque=500; prazo=2; transito=100; previsao_3m=120; vendas_1m=20; vendas_3m=60; estoque_minimo=30 | ml_valido | 1.000000 | 1.000000 | Não aplicável | Segunda inferência local; não é validação adicional de generalização do ML. |
| G14 | Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15 e avalie o impacto comercial na carteira e nas margens. | ml_composta | 1.000000 | 1.000000 | Não aplicável | Tarefa composta de ML e análise comercial, sem mapear atributos automaticamente de SKU. |
| G15 | Compare excesso de estoque, faturamento e descontos; consulte a política comercial antes de recomendar uma ação. | composta | 0.933333 | 1.000000 | Não aplicável | 14/15 fatos sustentados; aviso de indisponibilidade sem suporte nos snippets. Relevancy preservada. |

## Agregações

| Métrica | Casos | Média não ponderada | Abaixo de 0,8 | IDs |
|---|---:|---:|---:|---|
| faithfulness | 15 | 0.995555556 | 0 | Nenhum |
| answer_relevancy | 15 | 0.852854864 | 3 | G01, G04, G11 |

Oráculo DuckDB reexecutado localmente: 8/8 verificações aprovadas.
Sete casos não têm verificação financeira configurada; isso não significa reprovação nem aprovação determinística.
O limite usa comparação estrita (<0,8): G03=0,8 não entra na contagem. Doze casos têm ambas as notas ≥0,8.
Não confundir status evaluated (julgamento válido) com nota acima do limite. Notas baixas foram preservadas.
Protocolos históricos diferem em segmentação (ver fonte por métrica); médias descritivas não constituem comparação controlada entre protocolos.
G16–G18 não compõem esta amostra de 15. Não se conclui desempenho em perguntas ambíguas/fora de escopo a partir destes resultados.

## Origem por métrica

| Caso | Fonte Faithfulness | Fonte Answer Relevancy |
|---|---|---|
| G01 | `reports/evaluation/20261017T134931Z-two-cases/results.json` | `reports/evaluation/20261017T134931Z-two-cases/results.json` |
| G02 | `reports/evaluation/20261017T143219Z-batch-862a7b/results.json` | `reports/evaluation/20261017T142045Z-batch-d6b957/results.json` |
| G03 | `reports/evaluation/20261017T142045Z-batch-d6b957/results.json` | `reports/evaluation/20261017T142045Z-batch-d6b957/results.json` |
| G04 | `reports/evaluation/20261018T130925Z-pipeline-8d9806/judge-G04/results.json` | `reports/evaluation/20261018T130925Z-pipeline-8d9806/judge-G04/results.json` |
| G05 | `reports/evaluation/20261018T122104Z-batch-a8ba57/results.json` | `reports/evaluation/20261018T122104Z-batch-a8ba57/results.json` |
| G06 | `reports/evaluation/20261018T150953Z-pipeline-77be69/judge-G06/results.json` | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G06/results.json` |
| G07 | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G07/results.json` | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G07/results.json` |
| G08 | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G08/results.json` | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G08/results.json` |
| G09 | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G09/results.json` | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G09/results.json` |
| G10 | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G10/results.json` | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G10/results.json` |
| G11 | `reports/evaluation/20261018T135242Z-batch-93d58e/results.json` | `reports/evaluation/20261018T135242Z-batch-93d58e/results.json` |
| G12 | `reports/evaluation/20261017T134931Z-two-cases/results.json` | `reports/evaluation/20261017T141952Z-batch-7fcfdc/results.json` |
| G13 | `reports/evaluation/20261018T135451Z-batch-f873ad/results.json` | `reports/evaluation/20261018T135451Z-batch-f873ad/results.json` |
| G14 | `reports/evaluation/20261018T135451Z-batch-f873ad/results.json` | `reports/evaluation/20261018T135451Z-batch-f873ad/results.json` |
| G15 | `reports/evaluation/20261018T150421Z-pipeline-c0b11d/judge-G15/results.json` | `reports/evaluation/20261018T144839Z-batch-ae229a/results.json` |

As respostas completas, contextos recuperados, ferramentas, vereditos, fontes e hashes estão em `evidencias-avaliacoes.json`.
O CSV contém os valores numéricos sem arredondar para exibição. Não houve treino, inferência adicional nem julgamento novo nesta consolidação.
