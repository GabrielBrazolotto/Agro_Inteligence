# Retomada restrita a dois casos — 17/10/2026

## Escopo e reaproveitamento

Foram processados **somente G01 e G12** do golden. G02 foi inicialmente
selecionado, mas não chegou a ser executado. Foi substituído por G12 para
evitar chamadas de geração e manter ferramentas diferentes. Os outros 16
casos não foram executados na retomada real.

- **G01:** receita líquida faturada total. Resposta e contextos originais
  reaproveitados de `20261017T130820Z/results.json`, sem regeneração.
  Pergunta idêntica, snapshot comercial comparado ao DuckDB atual, trechos
  comparados aos documentos originais e valor revalidado por SQL independente.
  A resposta continua marcada como originalmente degradada; o aviso de análise
  comercial incompleta e o 429 histórico não foram apagados. Esses eventos não
  são tratados como falhas novas nem como motivo para bloquear o juiz atual.
- **G12:** backorder com estoque=10, prazo=8, trânsito=0, previsão_3m=100,
  vendas_1m=20, vendas_3m=60 e estoque_mínimo=15. Executou a mesma rota de ML
  local do Streamlit, com os sete atributos e o artefato scikit-learn existente.
  Não houve geração Gemini dessa resposta nem associação automática a um SKU.

## Resultados reais

| Caso | Resposta | Faithfulness | Answer Relevancy | Tokens do julgamento final |
|---|---|---:|---:|---:|
| G01 | R$ 493.126.517,02, somente faturadas de 01/10/2025 a 30/09/2026 | 1,000 (3/3 afirmações) | 0,667 (2/3 unidades) | 2.637 |
| G12 | Risco sinalizado, score 0,9267, limiar 0,91; score não calibrado | 1,000 (9/9 afirmações) | sem nota: `invalid_judgment` | 1.795 |

O juiz considerou o aviso operacional de G01 uma unidade não relevante; essa
decisão real foi preservada. Recomenda-se calibrar a rubrica com revisão humana
para reconhecer transparência operacional, sem remover avisos para melhorar scores.

Em G12, o juiz retornou `Atributos usados pelo modelo: ...`, que não é uma
citação verificável da resposta. A relevância inteira ficou sem nota, sem
descartar apenas a unidade problemática para elevar o score. A Faithfulness
usa outras afirmações válidas e foi calculada independentemente. Portanto
há **dois casos com alguma métrica**, **um completamente avaliado** e **um
parcialmente avaliado**. Isso não é reprovação da resposta ML.

Latências da última execução: G01 2.806,36 ms, G12 14.862,409 ms, incluindo
espera sequencial no segundo caso. Contextos completos, ferramentas, vereditos,
justificativas e latências estão em
`reports/evaluation/20261017T134931Z-two-cases/results.json` e `results.md`.
O check financeiro independente de G01 passou. Nenhum score representa
avaliação de generalização do classificador na cooperativa fictícia.

## Chamadas e falhas desta retomada

**6 requisições Gemini no total, todas ao juiz `gemini-3.1-flash-lite`:**

- 3 recusadas com HTTP 400 durante diagnóstico/correção do schema;
- 3 chamadas com resposta da API: uma tentativa preliminar e os dois
  julgamentos finais. A tentativa preliminar falhou na validação local de quotes.
- **0 chamadas Gemini de geração do chatbot**, **0 embeddings**, uma inferência
  scikit-learn local. Nenhuma chamada ao modelo principal ou ao 3.6 bloqueado.
- Não houve 429 ou timeout nesta retomada. Os bloqueios existentes não foram
  removidos, não houve troca automática de chave/modelo ou alteração de faturamento.

A API reportou **7.069 tokens conhecidos** nessas três respostas (4.641 input,
2.428 output). As três recusas não informaram uso: não se atribuiu zero a elas.
Esses números não são prova de cobrança; custos permanecem desconhecidos.
O inventário consolidado está em `session_calls.json` na pasta final, incluindo
os relatórios das tentativas anteriores. O ledger final isolado contém duas
chamadas; o consolidado contém as seis desta tarefa.

O diagnóstico sanitizado confirmou rejeição de campos do schema, sem preservar
mensagens brutas da API. O schema enviado agora usa um subconjunto expandido,
sem referências ou restrições adicionais incompatíveis. A validação Pydantic
completa (campos, tipos, limites, propriedades extras) permanece local.
A chamada seguinte foi aceita, comprovando compatibilidade dessa forma de envio.

Outra falha local era a exigência de igualdade literal de trechos, inclusive
Markdown. A validação agora aceita apenas remoção de negrito, backticks,
marcadores de lista e normalização de espaços. Não modifica palavras, números,
vereditos ou fontes. Reticências/paráfrases continuam inválidas. As métricas
são validadas independentemente, sem perder uma métrica válida por erro na outra.

Os vereditos recebidos foram revalidados **offline**, com zero chamadas extras.
As falhas de validação originais ficam preservadas no relatório. Não houve
refação de respostas nem alteração manual dos vereditos do juiz.

## Comandos

```powershell
cd D:\Agro-Intelligence-AI
# Somente dois casos, reuso validado, máximo de duas requisições do juiz:
.\.venv\Scripts\python.exe -m scripts.resume_evaluation --live --cases G01 G12 --reuse-from reports/evaluation/20261017T130820Z/results.json --interval 15 --max-calls 2
# Revalidar vereditos já recebidos, sem acesso remoto:
.\.venv\Scripts\python.exe -m scripts.replay_evaluation reports/evaluation/20261017T134931Z-two-cases
.\.venv\Scripts\python.exe -m pytest -q
```

Para produzir os relatórios históricos, também foram usados orçamentos 6, 4
e 3 nas tentativas interrompidas anteriores e uma chamada diagnóstica de G01.
O consolidado contabiliza tudo; esses comandos não devem ser repetidos para
recriar erros já diagnosticados. O comando atual não libera o lote de 18.

## Arquivos

Criados: `evaluation/resume.py`, `scripts/resume_evaluation.py`,
`scripts/replay_evaluation.py`, `tests/test_resume_evaluation.py`, esta documentação
e os relatórios da retomada. Alterados: `evaluation/judge.py`,
`evaluation/runner.py`, `tests/test_evaluation.py`, README e documentação de avaliação.
Streamlit, agentes, documentos, tabelas, embeddings, artefato ML e credenciais
não foram alterados nesta retomada.

Validação final: **152 testes aprovados**. A regressão cobre reuso sem regenerar,
rejeição de cache desatualizado/parcial, orçamento e limite de dois casos,
tokens cumulativos, interrupção por 429, normalização estritamente cosmética
e preservação de uma métrica válida quando a outra possui citação inválida.
