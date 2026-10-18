# G04: faturamento mensal e completude do cache

## Contrato e causa comprovada

Pergunta exata:

> Como evoluiu o faturamento por mês nos 12 meses disponíveis? Liste uma linha por mês no formato YYYY-MM com o valor exato.

São esperadas 12 linhas, de `2025-10` até `2026-09`, com os valores monetários
exatos de receita líquida **somente dos itens faturados**, em ordem cronológica.

O registro de geração `reports/evaluation/20261017T143301Z-batch-32dd30/results.json`
mostra `duckdb_comercial` e `chroma_rag_comercial` concluídos, timeout de
`gemini_analise` (referência `acde0309a51c`) e `gemini_sintese` bloqueada por limite
diário HTTP 429 (referência `b77b7adeebec`). Isso produziu um fallback factual.
Essas são as falhas registradas dessa geração; não são hipóteses sobre cota atual.

O DuckDB e o roteamento estavam corretos: `select_commercial_context` já selecionava
`mensal`, e a consulta fixa em `commercial_snapshot` agrupa por
`strftime(data_venda,'%Y-%m')`, ordena os períodos e calcula faturamento separado
da carteira. Não foi necessário modificar SQL, tabelas, documentos ou dados.
As evidências de G04 continham os 12 meses, mas `factual_answer` não renderizava
essa seção. A resposta resultante mostrou apenas totais e documentos.

O cache aceitava a resposta mesmo com falha de completude e preferia respostas
com mais métricas válidas. Por isso a execução de 18/10 reutilizou esse fallback.
O relatório `reports/evaluation/20261018T122104Z-batch-a8ba57/results.json` preserva
Faithfulness 1,000 e Relevancy 0,000, com falha determinística mensal. Suporte dos
fatos presentes não comprova atendimento à pergunta nem presença de todos os dados.

## Correção

- O fallback agora apresenta todas as linhas recuperadas de `mensal`, com mês e
  valor em reais e centavos. Total conferido localmente: **R$ 493.126.517,02**.
- As instruções de geração explicitam o formato e a série completa.
- Respostas Gemini mensais são temporariamente acumuladas antes de exibir o texto,
  para verificar a presença de todos os meses e valores. Se a saída estiver
  incompleta, a resposta usa os resultados reais do DuckDB como resumo factual,
  marcando `gemini_sintese` como `rejected/incomplete_monthly_response`. Não há
  nova chamada para tentar completar nem previsão de valores ausentes.
- O cache valida completude mensal antes de reutilizar uma resposta: exige
  evidência mensal, 12 períodos no contrato de G04, uma linha por mês com `YYYY-MM`
  e `R$`, valores exatos com tolerância inferior a meio centavo, sem duplicações.
  Datas completas de cabeçalhos não contam como linhas mensais duplicadas.
- Respostas antigas inelegíveis permanecem armazenadas com suas notas e origens;
  `rejected_cached_responses` as identifica. Na consolidação, G04 pode aparecer
  como `response_incomplete`, com execução histórica reconhecida, sem apagar o zero.
  A seleção não descarta respostas simplesmente por terem notas baixas.
- Uma nova resposta incompleta é registrada para auditoria, mas não é reutilizável
  e não é enviada ao juiz: métricas ficam sem nota com `incomplete_response`.
  A validação é específica do contrato mensal; não representa avaliação semântica
  de completude para todos os demais tipos de pergunta.

## Reteste preparado, não executado nesta alteração

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --cases G04 --live --interval 15 --max-calls 10
```

Não usar `--judge-only`: a resposta anterior está incompleta e precisa ser gerada
novamente pelo fluxo corrigido. O comando seleciona somente G04, respeita os limites
existentes e grava relatório novo. As notas antigas não serão migradas para uma
resposta diferente. Nova nota depende de geração e julgamento reais bem-sucedidos.
Nenhum caso adicional foi autorizado ou executado nesta correção.

## Verificação local

Testes de regressão conferem ferramenta mensal contra oráculo SQL independente,
ano/mês, 12 períodos, soma, fallback completo, bloqueio de saída Gemini incompleta,
valores errados, períodos ausentes/duplicados, evidência truncada, cache histórico
com notas válidas e bloqueio do juiz para resposta nova incompleta. Chamadas SDK
nos testes usam mocks. Não houve chamada real ao Gemini nesta alteração.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

O manifesto `reports/evaluation/g04_before_fix_hashes.json` registra hashes do
relatório histórico e cache, para conferência de preservação após os testes.

Resultado: **184 testes aprovados em 41,48 s**, incluindo 10 regressões de G04;
essas 10 regressões também passaram isoladamente após a restrição da proteção
a perguntas sobre faturamento/receita. `pip check` não encontrou incompatibilidades.
**33 arquivos históricos/cache** conferidos por SHA-256 permaneceram inalterados.
Nenhum teste de geração real ou novo julgamento Gemini foi executado.
