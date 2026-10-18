# Faithfulness de G06 e G15: auditoria e retomada restrita

## Estado confirmado

O cache atual contém 13 casos com as duas métricas válidas. G06 e G15 têm
resposta salva e Answer Relevancy 1,000; Faithfulness continua sem nota.
Nenhum caso foi gerado novamente e nenhuma chamada real foi realizada nesta alteração.

## Artefatos originais e causas exatas

| Caso | Relatório original do julgamento |
|---|---|
| G06 | `reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G06/results.json` |
| G15 | `reports/evaluation/20261018T144839Z-batch-ae229a/results.json` |

Nos dois JSONs foram conferidos `calls[].raw_judgment`,
`results[].current_assessment.rejected_faithfulness_judgment`, a resposta,
evidências e a métrica histórica. Os vereditos da avaliação coincidem com os
vereditos brutos preservados no ledger. O parser não alterou os campos.

**G06: claim `c006`**

```json
{"claim_id":"c006","factual":false,"supported":true,"snippet_ids":[],"reason":"Título sem afirmação factual."}
```

Trecho original: `**Observações e Regras Aplicadas:**`.
Não é uma referência inexistente. A inconsistência é `factual=false` e
`supported=true`, proibida pelo contrato local: uma unidade sem fato tem
`supported=false` e referências vazias. O diagnóstico específico agora é
`nonfactual_marked_supported`, mantendo o status histórico `invalid_evidence_reference`.

**G15: claim `c019`**

```json
{"claim_id":"c019","factual":true,"supported":true,"snippet_ids":[],"reason":"Aviso sobre limitação de análise do agente."}
```

Trecho original: o aviso de que uma análise de agente ficou indisponível e a
resposta ficou com limitação. O juiz marcou uma afirmação como factual e sustentada,
mas não indicou qualquer evidência. Diagnóstico: `factual_supported_without_evidence`.
O log de ferramenta registra HTTP 504 na análise comercial, mas logs de execução
não constavam nos trechos de evidência enviados ao juiz. Não se pode acrescentá-los
retroativamente e fingir que foram utilizados na avaliação.

G06 possui 126 snippets (`s0001` a `s0126`) e nove unidades de resposta; G15 possui
393 snippets (`s0001` a `s0393`) e 19 unidades. IDs de evidências raiz são `e1/e2`
em G06 e `e1/e2/e3/e4` em G15. As duas falhas são listas de referências **vazias**,
não IDs deslocados, inexistentes ou começando em zero. A numeração inicia em um.
Não foi encontrada falha no parser ou na associação dos IDs desses julgamentos.

## Correção sem mudar critérios

A validação já rejeitava corretamente esses dois vereditos. Não foi relaxada.
O problema comprovado do protocolo era o contrato de não factuais estar implícito
na validação, sem instrução explícita para `supported=false` nesse caso. As instruções
e descrições de campos agora explicitam essa combinação e a exigência de referência
para todo fato classificado como sustentado. Um fato sem prova deve receber
`supported=false` e justificar a ausência; não se transforma automaticamente um
aviso em não factual ou uma afirmação sem prova em fato sustentado.

O protocolo de cálculo permanece `indexed_claim_evidence_v2`, com as mesmas unidades,
denominador e regras. A revisão de instruções é registrada como
`v2_explicit_nonfactual_contract_20261018` em novas avaliações.
Julgamentos inválidos agora incluem diagnóstico por claim e as tabelas de unidades
e snippets, permitindo conferir as referências sem gastar outra chamada.

## Resultado da revalidação offline

Ambos permanecem `invalid_judgment`, com score **nulo**. Uma correção de parser não
resolve contradições que já estavam nos vereditos originais. Não foram corrigidos
os booleanos nem escolhidos IDs pelo programa, porque isso substituiria o julgamento.
Não foi gravada nenhuma nova métrica no cache e a Relevancy 1,000 foi preservada.
Para completar 15 avaliações tecnicamente válidas, faltam dois novos julgamentos
válidos de Faithfulness; não se promete que suas notas serão 1,000.

Auditoria reproduzível, **sem API**, com saída em uma pasta nova:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_faithfulness --cases G06 G15 --reports reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G06/results.json reports/evaluation/20261018T144839Z-batch-ae229a/results.json
```

O JSON derivado conserva hashes dos relatórios, resposta, contexto, veredito bruto,
IDs, diagnóstico e score nulo. O payload é reconstruído a partir das evidências
salvas, identificado como reconstrução; não é apresentado como captura HTTP original.
O comando não escreve no cache e recusa sobrescrever uma pasta de auditoria existente.
Auditoria desta alteração: `reports/evaluation/20261018T145445Z-faithfulness-audit-008c04/`.

## Comandos separados para novos julgamentos, ainda não executados

Primeiro, confira o plano e o orçamento, sem chamar Gemini:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --dry-run --phase judge --cases G06 G15 --daily-limit 20 --reserve-demo 5 --max-calls 2
```

Os dois casos mostram `pending_metrics: ["faithfulness"]`, sem geração nova.
A opção `--cases` restringe a execução para não selecionar outros casos pendentes.

Somente **após autorização e disponibilidade de orçamento/cota**, um por vez:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --phase judge --cases G06 --interval 15 --daily-limit 20 --reserve-demo 5 --max-calls 1
```

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --phase judge --cases G15 --interval 15 --daily-limit 20 --reserve-demo 5 --max-calls 1
```

São reutilizadas a resposta e as evidências de cada caso; a métrica Relevancy já
válida não é solicitada. As falhas históricas dos agentes não disparam nova análise.
Os novos relatórios são separados dos originais. A repetição do comando após uma
métrica válida não dispara nova chamada.

**Impedimento atual:** o contador local do Lite registra 15 chamadas diárias,
com limite 20 e reserva cinco: saldo para avaliação **zero**. Com essa política,
os comandos live acima serão bloqueados antes do envio enquanto o saldo estiver
esgotado. Não houve aumento de limite, redução de reserva ou remoção de contador.
Concluir hoje requer validar a cota real disponível e decidir explicitamente sobre
uma eventual revisão do orçamento local, além de autorizar as chamadas. Saldo
local não é consulta à cota efetiva do Google; chamadas de outros scripts/máquinas
podem não estar contabilizadas. Não há garantia de conclusão hoje sob a política atual.

## Testes e arquivos

Testes reproduzem os dois vereditos reais, preservam hashes/valores, rejeitam IDs
zero/inexistentes/duplicados, mantêm nota zero legítima para fato sem suporte e
verificam que a seleção de G06 julga apenas sua Faithfulness, sem executar agentes
nem alterar G15 ou a Relevancy válida. SDK é simulado nos testes.

Alterados: `agro_ai/evaluation/faithfulness.py`, `judge.py`, `pipeline.py`,
`scripts/evaluation_pipeline.py`, testes e README. Criados
`agro_ai/evaluation/faithfulness_audit.py`, `scripts/audit_faithfulness.py`,
`tests/test_faithfulness_audit.py` e esta documentação.
O manifesto `reports/evaluation/g06-g15-before-audit.json` registra os hashes
anteriores dos relatórios originais e cache para comprovar preservação.

Resultado local: **206 testes aprovados em 43,67 s**; `pip check` sem incompatibilidades.
Novas chamadas reais ao Gemini: **zero**. Os dois julgamentos foram revalidados
offline e permaneceram inválidos; nenhuma métrica foi promovida para o cache.
