# Revisão G01/G12 e preparação dos 16 casos restantes

## Justificativa real de G01

No relatório histórico `reports/evaluation/20261017T134931Z-two-cases/results.json`,
o juiz considerou relevantes duas unidades: receita/período e detalhes da
apuração. Marcou o aviso de análise comercial incompleta como não relevante:

> Trata-se de metadados sobre o processo de geração da resposta, sem valor para a gestão comercial.

Logo, Answer Relevancy foi **2/3 = 0,667**. Essa é a justificativa registrada,
não uma dedução sobre o faturamento. A receita **R$ 493.126.517,02** foi
conferida pelo oráculo SQL; Faithfulness foi **1,000**. O aviso não foi apagado
para aumentar nota. A rubrica pode ser discutida com revisão humana em outro
experimento, sem substituir os resultados atuais.

## Correção de citações e formato

O antigo juiz de G12 devolveu `Atributos usados pelo modelo: ...`. Essa
abreviação não é citação verificável: a nota de Relevancy permanece ausente
no histórico. Nenhum parser transforma reticências ou paráfrases em evidência.

O protocolo novo de Relevancy (`indexed_answer_lines_v2`) segmenta a resposta
em linhas não vazias, com ID, texto original e offsets. O juiz devolve apenas
`unit_id`, booleano de relevância e justificativa para **cada** unidade. O sistema
resolve o ID no trecho real; o juiz não precisa copiar Markdown ou números.
IDs inventados, ausentes ou duplicados invalidam a métrica inteira, sem
descartar unidades desfavoráveis do denominador. Tipos, campos extras,
limites e cobertura são validados localmente com Pydantic.

O critério continua pertinência à pergunta, distinguindo correção factual.
A segmentação passou a ser determinística: scores v1/v2 têm versões e
denominadores diferentes e não devem ser comparados como se o protocolo fosse
idêntico. A nota antiga de G01 não foi recalculada. Faithfulness mantém a
proporção de afirmações sustentadas, sem alterar sua nota válida de G12.

Quando ambas faltam, o juiz pode avaliá-las em uma chamada estruturada. Quando
somente uma falta, o schema/prompt solicita somente essa métrica. Uma falha
não produz zero. `not_applicable` é resolução explícita sem score, não reprovação.

## Resultado real desta alteração

Foi executado somente:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --cases G12 --judge-only --live --interval 15 --max-calls 1
```

Resposta/contexto e Faithfulness válidos de G12 vieram do cache. Houve **uma
única chamada** ao juiz `gemini-3.1-flash-lite`, que retornou **HTTP 503** após
aproximadamente 8,5 segundos. Não houve veredito ou informação de tokens.
Não se presume falta de cota ou timeout. Não houve retry, nova geração,
inferência ML, embedding ou execução dos outros 16 casos.

Resultado preservado: G01 F=1,000 / R=0,667; G12 F=1,000 / R=sem nota.
O novo protocolo passou em testes locais com mocks; sua validação remota com
resposta bem-sucedida ainda está pendente. Não foram inventados custos ou scores.

Evidências da tentativa:
`reports/evaluation/20261017T140620Z-batch-92ce1f/results.json`, `results.md`
e `consolidated.json`. O planejamento atual está em
`reports/evaluation/remaining_plan.json`.

## Cache persistente e imutabilidade

Antes havia arquivos de respostas/contextos/vereditos e reuso limitado a G01,
mas nenhum cache geral por resposta e métrica para retomar os 18 casos. Agora
`data/runtime/evaluation_cache/` contém:

- Respostas e evidências originais, identificadas pelo conteúdo e pergunta.
- Fingerprints do DuckDB, documentos e artefato/metadados ML. Alteração das
  referências invalida o reuso; conteúdo antigo permanece preservado.
- Métricas válidas separadas por resposta, com protocolo, veredito, origem e
  hash do relatório original. Resultados baixos válidos também são reutilizados.
- Eventos append-only de tentativas/falhas. Erros e métricas inválidas não
  ocupam o cache de métricas válidas.

A importação explícita de G01/G12 validou snapshots financeiros/documentais e
o contrato/artefato ML, sem gerar previsões. Os vereditos válidos foram conferidos
offline e copiados; originais não foram escritos. Há duas respostas/contextos,
duas métricas válidas em G01 e somente Faithfulness válida em G12.

Cache usa arquivos imutáveis com checksums. Reexecutar caso completo não cria
cliente do juiz nem repete ferramentas. Caso parcial só solicita a métrica
pendente. Corrupção de cache falha de forma explícita, sem apagar dados para
forçar nova execução. Os fingerprints são conservadores: mudança de referência
exige nova validação/execução autorizada. O cache não é contador de cota da conta.

O relatório histórico conserva o SHA-256:
`a650026fa6bd4a2a5a65b0260302af860f6e96e7c18d2e3f969324947e791e35`.
Os demais relatórios históricos também não foram modificados. O comando antigo
de replay agora grava uma cópia derivada em outra pasta e recusa sobrescrever
uma pasta existente.

## Consolidação

O planejamento consolida **18 casos**: 2 com respostas existentes, 1 totalmente
avaliado (G01), 1 parcialmente avaliado (G12), 16 não executados. A falha de
infraestrutura 503 é um indicador adicional sobre G12; não é uma reprovação
nem uma terceira pergunta executada. Por isso indicadores de infraestrutura
podem se sobrepor ao estado de execução/avaliação.

`metrics` conserva score/status e origem por métrica; `infrastructure_failure`
separa falhas de API/transporte/orçamento. Perguntas sem resposta ficam como
falha operacional ou não executadas; respostas parciais descartadas pelo chat
não são avaliadas. Métricas não aplicáveis/ausentes não entram nas médias.

## Comandos para retomar — não executados automaticamente

```powershell
cd D:\Agro-Intelligence-AI
# Planejar/importar os resultados históricos; ZERO chamadas remotas:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches plan --import-report reports/evaluation/20261017T134931Z-two-cases/results.json --batch-size 2

# Somente a pendência de G12, quando houver disponibilidade e nova solicitação:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --cases G12 --judge-only --live --interval 15 --max-calls 1

# Executar SOMENTE o próximo lote de 2 dos 16 restantes, após autorização:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --next --batch-size 2 --live --interval 15 --max-calls 12

# Alternativa: planejar lotes de 3 (sem rede):
.\.venv\Scripts\python.exe -m scripts.evaluation_batches plan --batch-size 3
# Executar SOMENTE um lote de até 3, após autorização:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --next --batch-size 3 --live --interval 15 --max-calls 18
```

Cada comando `run --next` executa **um único lote e termina**. Não há laço
para processar todos. O primeiro lote planejado de 2 é G02/G03; os seguintes
são G04/G05, G06/G07, G08/G09, G10/G11, G13/G14, G15/G16 e G17/G18.
Em lotes de 3, os 16 se distribuem em 3/3/3/3/2/2. O planejamento é recalculado
com o cache, sem repetir casos completos; parciais só retomam suas pendências.
G01/G12 não entram em `--next`: pendências do baseline usam `--cases G12`.

Os controles de `api_limits.py` permanecem: serialização, intervalo configurado,
Retry-After, bloqueio diário persistente e SDK sem retries internos. O lote
para na primeira falha de geração/julgamento ou limite; respostas e métricas
válidas obtidas antes disso ficam disponíveis para a próxima solicitação.
Qualidade baixa válida não é falha de infraestrutura. Não use vários processos
em paralelo e não apague bloqueios para forçar chamadas. Nenhuma chave, modelo
ou configuração de faturamento foi trocada nesta alteração.

Use as ferramentas novas para retomadas deduplicadas. Os comandos antigos de
avaliação completa permanecem por compatibilidade e não oferecem a mesma
deduplicação global; não os use para executar esses 16 casos.

## Arquivos

Criados: `evaluation/cache.py`, `evaluation/batches.py`,
`scripts/evaluation_batches.py`, `tests/test_evaluation_batches.py`, esta
documentação, cache local, planejamento e relatório da tentativa de G12.
Alterados: `evaluation/judge.py`, `evaluation/runner.py`, `evaluation/resume.py`,
`scripts/replay_evaluation.py` e documentação. Não foram alterados Streamlit,
DuckDB comercial, documentos RAG, Chroma, modelo ML ou credenciais.

Validação final: **160 testes aprovados**, `pip check` sem conflitos. Inclui
cobertura integral por IDs, rejeição de IDs inválidos/duplicados/ausentes,
imutabilidade de notas válidas baixas, detecção de alteração de referências,
integridade do cache, reuso sem geração, seleção de somente uma métrica,
interrupção por 429, retomada sem novas chamadas após completar o cache,
planejamento sem SDK/rede, não aplicáveis sem nota inventada e replay derivado
sem sobrescrever a origem. Essas verificações usam mocks; não são scores reais.
