# Correção de Faithfulness de G02

## Diagnóstico confirmado nos registros

Foram inspecionados `results.json`, `calls[].raw_judgment`,
`current_assessment.faithfulness_judgment`, resposta e contexto de G02 em:

- `reports/evaluation/20261017T142045Z-batch-d6b957`;
- `reports/evaluation/20261017T142342Z-batch-6e8c73`.

O protocolo antigo exigia `quote` literal da **resposta**, não da evidência.
Aceitava remoção de negrito, crases e espaços, mas não itálico simples.

Na primeira execução, as seis citações rejeitadas eram campos do JSON de evidência,
ausentes literalmente da resposta:

```text
rupturas_observadas": 60
posicoes": 3000
rupturas_com_carteira": 41
carteira_em_ruptura": "4399084.73"
insuficiencias_com_saldo": 695
pares_sinalizados": 755
```

Na segunda, somente esta citação foi rejeitada:

```text
insuficiência com saldo positivo (695 posições
```

O original é `*insuficiência com saldo positivo* (695 posições`.
O juiz removeu a marcação de itálico: não houve paráfrase semântica nesse trecho,
mas a comparação antiga não normalizava o asterisco simples. Nas duas tentativas
houve resposta válida da API; `invalid_quote` era falha de validação do veredito,
não comprovação de alucinação, falta de cota ou erro na contagem comercial.

O contexto efetivamente recuperado é `e1`, origem `estoque.abastecimento`:
60 rupturas observadas, 3.000 posições, 41 rupturas com carteira,
R$ 4.399.084,73 em carteira nessas posições, 695 insuficiências com saldo
e 755 pares sinalizados. Contexto não foi substituído por referência inventada.

## Protocolo novo

`indexed_claim_evidence_v2` elimina cópia livre de citações nas novas chamadas.
O sistema indexa cada linha não vazia da resposta em `c001`, etc., mantendo
texto e offsets originais. Cada unidade pode conter vários fatos: todos devem
estar sustentados para `supported=true`. O juiz identifica explicitamente linhas
sem fato; elas são excluídas do denominador com justificativa, nunca silenciosamente.

Os trechos `s0001`, etc. são folhas dos JSONs realmente recuperados, com
`evidence_id`, origem, caminho JSON Pointer e valor original. Textos documentais
são mantidos como texto original. Não se usam respostas de referência fabricadas
nem análise de agente LLM como prova. A seleção de quais fatos são sustentados
continua sendo avaliação semântica do juiz, não uma regra de coincidência de números.

O juiz retorna `claim_id`, `factual`, `supported`, `snippet_ids` e `reason`.
A validação local exige cobertura exata, booleanos estritos, IDs existentes,
ausência de duplicações, justificativa não vazia e evidência para cada fato
classificado como sustentado. Exclusões não factuais não podem ter suporte ou
referências. Citações livres extras, inclusive paráfrases, são rejeitadas pelo schema.
As citações auditáveis são resolvidas localmente e preservadas no relatório novo.

Referências inválidas ou justificativa ausente resultam em julgamento inválido
com nota nula; não são convertidas em zero. Fatos julgados sem suporte recebem
false e entram no denominador. A consistência semântica da justificativa e as
exclusões não factuais ainda dependem do juiz e requerem auditoria humana.
O protocolo conta unidades por linha, não afirmações atômicas livres: scores v1
e v2 não são diretamente comparáveis. Não houve reinterpretação de notas antigas.

## Preservação e execução

Não foram realizadas chamadas reais à API nesta alteração. Os relatórios antigos,
resposta/contexto em cache e Answer Relevancy 1,000 de G02 foram preservados.
Faithfulness de G02 permanece **sem nota**. O manifesto
`reports/evaluation/g02_before_fix_hashes.json` permite verificar os arquivos
históricos e cache comparados antes/depois.

Quando houver autorização e cota, executar somente o julgamento pendente:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --cases G02 --judge-only --live --interval 15 --max-calls 1
```

O executor existente reutiliza a resposta/contexto e a Relevancy válida do cache;
solicita somente Faithfulness, grava relatório novo e não regenera o chatbot.
Não executar esse comando para testar localmente a correção.

Testes locais, sem chamadas reais:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Os testes cobrem resolução exata, suporte e ausência de suporte, cobertura incompleta,
IDs inexistentes, duplicações, justificativas vazias, booleanos inválidos,
paráfrases indevidas e reprodução das duas falhas históricas reais.

Resultado local desta alteração: **174 testes aprovados em 37,99 s**;
`pip check`: nenhuma dependência incompatível. Comparação SHA-256 de **22 arquivos**
de relatórios históricos/cache: nenhum modificado. Chamadas reais à API: **zero**.
Os testes SDK usam mocks; isso não comprova desempenho ou validade de um futuro
veredito Gemini real. Nenhuma nota retroativa foi atribuída a G02.
