# Avaliação automática — Etapa 2 / AI Factory PUCPR

## Implementação

Foi escolhida uma solução **equivalente ao DeepEval**, com juiz Gemini e
vereditos estruturados Pydantic. Não se usa o pacote DeepEval e não se afirma
equivalência numérica com seus scores. O módulo usa o SDK google-genai já
instalado, evita dependências conflitantes e solicita as duas métricas numa
única chamada para reduzir consumo. Pydantic tem versão explícita no requirements.

A distinção entre fundamentação nas evidências e pertinência à pergunta segue
os conceitos documentados em [Faithfulness](https://deepeval.com/docs/metrics-faithfulness)
e [Answer Relevancy](https://deepeval.com/docs/metrics-answer-relevancy).

`agro_ai/chatflow.py` é a rota compartilhada pelo Streamlit e avaliador. Usa
os mesmos agentes, consultas, recuperação Chroma, guardas de ML, streaming,
fallback e tratamento de resposta parcial. A rota ML pura continua local,
sem Gemini para calcular a previsão. Um callback captura o resultado efetivo
da inferência para avaliação, sem executar o modelo duas vezes. Langfuse mantém
os mesmos spans e não recebe texto de perguntas, respostas ou evidências.

## Golden dataset

[18 casos versionados](../data/evaluation/golden.json), cada um com ID, pergunta,
categoria, comportamento esperado, ferramentas esperadas e referência confiável:

| Casos | Tema | Referência |
|---|---|---|
| G01, G04 | Receita total e mensal | SQL independente de faturadas |
| G02, G03 | Ruptura observada e excesso | Estoque, saldo zero e máximo |
| G05, G06 | Regiões e margens | Receita líquida e custo de faturadas |
| G07–G09 | Aprovação, vista e desconto vedado | PC-001, política recuperada |
| G10, G11 | Rupturas com carteira e pendentes | EXISTS por produto/centro; somente pendentes |
| G12, G13 | Dois conjuntos válidos com sete entradas ML | Artefato treinado e contrato de atributos |
| G14, G15 | Tarefas dos dois agentes | Inferência real, ferramentas e RAG |
| G16, G17 | Ambiguidade e fora de escopo | Contrato do assistente comercial |
| G18 | ML sem entradas suficientes | Contrato dos sete atributos, sem inferência |

Não há respostas financeiras fixadas manualmente no golden. O oráculo é SQL
somente leitura, fixo, agregado e limitado, independente das funções comerciais
do aplicativo. Os documentos RAG originais não foram substituídos. Os casos
de esclarecimento/recusa representam comportamento desejado; o golden não
afirma que o roteador atual já o satisfaz. ML continua avaliado separadamente
com o dataset público; estes exemplos não são métricas de generalização de ML.

## Métricas e evidências

O juiz recebe apenas pergunta, resposta efetivamente recebida e evidências
efetivamente usadas pela rota: retornos DuckDB, trechos devolvidos pelo Chroma
e resultado do modelo local quando ocorreu inferência. Não recebe o golden,
resposta esperada, oráculo SQL, documentos não recuperados ou análises LLM
como fontes de prova. A proveniência de cada evidência tem um ID.

- **Faithfulness**: número de afirmações factuais sustentadas dividido pelo
  número de afirmações julgadas. O juiz extrai trechos literais, decide suporte
  e aponta IDs existentes. Contradições ou afirmações sem suporte não contam
  como sustentadas. A extração/veredictos/justificativas ficam no JSON.
- **Answer Relevancy**: unidades pertinentes divididas por unidades julgadas
  da resposta. Considera esclarecimento e recusa adequada ao domínio.
- Scores têm faixa 0–1; limiar inicial de revisão **0,8**, sem calibração empírica.
  Esses scores medem precisão das unidades, não cobertura completa da tarefa.
  Omissões exigem ler justificativas, ferramentas esperadas e checks específicos.
- Sem resposta, sem juiz, JSON inválido, HTTP 429 ou timeout: `score: null`,
  status separado. Nunca zero para avaliação que não ocorreu. Sem evidência ou
  afirmações factuais, Faithfulness é `not_applicable`, sem nota.
- Ausência de trechos literais ou referências inválidas invalida a avaliação,
  sem gerar score. Não se converte erro operacional em falha de qualidade.

O juiz pode errar, omitir afirmações ou ser afetado por conteúdo adversarial.
O prompt trata tudo como dados não confiáveis e usa schema, mas isso não
elimina ataques. Gerador e juiz usam o mesmo modelo configurado: existe viés
correlacionado. Recomenda-se revisão humana e um juiz independente numa etapa futura.

## Verificações determinísticas

`evaluation/reference.py` executa diretamente no DuckDB consultas para receita,
custo/margem, carteira, rupturas, excesso, meses e regiões. Carteira em ruptura
usa EXISTS, evitando multiplicação de linhas. A margem regional é
`100*SUM(receita_liquida-custo_total)/SUM(receita_liquida)`, só faturadas.

Checks confrontam os valores solicitados na resposta com o SQL, sem pedir
opinião do juiz. Tolerância de R$ 0,005 e 0,005 ponto percentual. Valores
regionais/mensais precisam estar associados ao grupo na mesma linha; os casos
pedem esse formato. Ausência, arredondamento excessivo ou troca entre regiões
falham. Outra apresentação pode exigir revisão humana do check. Não são
checados todos os números espontaneamente mencionados na resposta. Os testes
também reconciliam somas mensais/regionais com o total e detectam inclusão
indevida de carteira e erro de centavos.

## Execução no Windows

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
# Sem --live: relatório não executado, sem chamadas remotas:
.\.venv\Scripts\python.exe -m scripts.evaluate_chat
# Amostra limitada, consome cota Gemini:
.\.venv\Scripts\python.exe -m scripts.evaluate_chat --live --max-cases 2
# Bateria: só avança além dos dois primeiros se a amostra funcionar:
.\.venv\Scripts\python.exe -m scripts.evaluate_chat --live --interval 15 --max-calls 80
```

Credenciais Gemini permanecem no `.env`; não há chave nova do juiz. Langfuse
continua opcional. Concorrência é **1**, intervalo padrão de **15 segundos entre
requisições**, incluindo embeddings, análises, síntese, juiz e retry 503.
Orçamento máximo de chamadas inclui tentativas. O adaptador não repete 429.
Após cada pergunta, 429 abre o circuito e não inicia juiz nem próximos casos.
Uma falha intermediária pode ser seguida pela síntese da mesma pergunta, pois
isso preserva exatamente o comportamento do chatbot; a interrupção da bateria
acontece ao fim dessa pergunta. Falhas do juiz/protocolo também param a bateria.
Uma amostra com erros operacionais não libera os casos restantes.

Relatórios JSON/Markdown são gravados em `reports/evaluation/<run_id>/` após
cada caso, com respostas, evidências sintéticas, scores, status, falhas, latências,
ferramentas, checks financeiros e propostas de melhoria. O JSON tem hash do
golden e suas definições completas. A versão original desta execução está em
`golden_snapshot.json`, com hash verificado. `scheduled_calls`
conta chamadas iniciadas, não cobranças. Uso do juiz só é registrado quando
retornado pela API. Custo fica desconhecido; nenhum preço é estimado.
As médias excluem erros e não aplicáveis; são publicadas com seu denominador.
Não publicar relatórios com dados comerciais reais sem revisão de privacidade.
O comando original não tem cache de respostas e pode consumir cota novamente.
A [retomada restrita a dois casos](retomada-avaliacao-dois-casos.md) oferece
reuso validado e revalidação offline de vereditos, com inventário de chamadas.
Para continuar sem repetir métricas válidas, use a
[preparação por lotes e cache persistente](retomada-lotes-etapa2.md).
O replay legado agora cria uma cópia derivada e preserva o relatório de origem.

## Resultado real desta implementação

Em `reports/evaluation/20261017T130820Z/`, houve **1 pergunta executada** (G01),
**1 resposta recebida**, status `degraded`, e **0 perguntas avaliadas pelo juiz**.
A análise comercial recebeu **HTTP 429**; a síntese final devolveu a receita
correta e aviso da análise incompleta. O oráculo confirmou **R$ 493.126.517,02**:
**1 check financeiro passou**. Os outros 17 casos ficaram não executados.

Faithfulness e Answer Relevancy: **sem score**, sem média; não foram chamadas
após o 429. Não se pode concluir qualidade geral por essa execução, nem afirmar
sucesso remoto do juiz. A estrutura e o parsing do juiz foram testados com
mocks; os resultados desses testes não são scores reais de avaliação.

Melhorias concretas: verificar os limites Gemini antes de retomar; preservar
15s ou aumentar o intervalo em nova execução; revisar os vereditos com amostra
humana; validar os casos de ambiguidade antes de adicionar roteamento novo;
investigar formatação/roteamento caso checks regionais falhem. Não alterar
respostas ou golden para esconder falhas de qualidade.

## Arquivos

Criados: `agro_ai/chatflow.py`, `agro_ai/evaluation/__init__.py`,
`agro_ai/evaluation/judge.py`, `agro_ai/evaluation/reference.py`,
`agro_ai/evaluation/runner.py`, `data/evaluation/golden.json`,
`scripts/evaluate_chat.py`, `tests/test_evaluation.py`, esta documentação e
os relatórios JSON/Markdown/snapshot em `reports/evaluation/20261017T130820Z/`.
Alterados: `app.py`, `agro_ai/ml/inference.py`, `requirements.txt` e `README.md`.
Não foram alterados documentos RAG, tabelas ou artefato do modelo ML.

Validação final: **136 testes aprovados** na suíte completa; `pip check` sem
conflitos. Os 12 testes específicos da avaliação cobrem referências golden,
oráculo financeiro e reconciliação, troca de valores entre regiões, proveniência
real, schema/uso do juiz com mock, ausência de nota em erros, resposta parcial,
limites de chamadas, interrupção da bateria por 429 e inferência ML local.
