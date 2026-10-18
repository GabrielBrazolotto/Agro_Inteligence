# Agro Intelligence AI

Assistente de gestão comercial de insumos agrícolas para a disciplina **AI Factory
da PUCPR**, implementado com Python, Streamlit, DuckDB, ChromaDB e Gemini.
Todos os clientes, produtos, vendas e documentos são fictícios.

Base ampliada de cooperativa: **5.000 clientes, 1.000 produtos, 8.000 pedidos,
20.000 linhas comerciais, 3.000 posições produto/centro, 5 regiões, 15 centros e
12.000 preços históricos**. Período fixo: outubro/2025 a setembro/2026.
Veja [geração, esquema, cenários e limites](docs/base-sintetica.md).

## Executar no Windows (PowerShell)

Recomendado: Python 3.11 de 64 bits e acesso à internet para instalar dependências
e utilizar Gemini. Na pasta do projeto:

```powershell
cd D:\Agro-Intelligence-AI
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Preencha `GEMINI_API_KEY` no `.env` com sua própria chave do
[Google AI Studio](https://aistudio.google.com/apikey). Nunca versione esse arquivo.
`GEMINI_MODEL` e `GEMINI_EMBEDDING_MODEL` são configuráveis; os padrões são
`gemini-3.5-flash` e `gemini-embedding-001`. O modelo de geração foi atualizado após
o 404 do Gemini 2.5 Flash e um teste real bem-sucedido com Gemini 3.5 Flash.
A disponibilidade depende da conta
e do ciclo de vida dos modelos; ajuste o `.env` caso a API indique modelo indisponível.

As análises dos agentes e o juiz agora têm variáveis separadas:
`GEMINI_AGENT_MODEL` e `GEMINI_JUDGE_MODEL`. O `.env.example` recomenda
`gemini-3.1-flash-lite`, confirmado pela listagem da API e por um teste mínimo
de streaming/JSON. `GEMINI_MIN_INTERVAL_SECONDS=15` controla espaçamento;
Retry-After e limites diários geram bloqueios persistentes, sem retry de 429.
Embedding-001 e o índice existente de 768 dimensões permanecem iguais. Veja
[modelos, defaults, evidências e limites](docs/modelos-e-limites.md).

```powershell
.\.venv\Scripts\python.exe -m scripts.init_data
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra `http://localhost:8501`. Não é necessário ativar o ambiente virtual nem mudar
a política de execução do PowerShell, pois os comandos chamam o executável diretamente.
Se `py` não existir, use `python -m venv .venv` com Python 3.11 instalado.
Para encerrar o servidor, pressione `Ctrl+C` no terminal.

Sem chave, o app permite visualizar os dados e mantém o chat desabilitado. Reinicie
o Streamlit após alterar o `.env`. Não cole a chave no chat, no código ou em capturas.

## Funcionalidades e fluxo

1. A inicialização valida os CSVs e carrega um novo DuckDB de forma atômica e
   idempotente, usando a assinatura dos dados e a versão do schema.
2. O app mostra vendas e totais por status e mantém mensagens em `session_state`.
3. Na primeira pergunta, divide os três documentos Markdown em trechos de 900
   caracteres, com sobreposição de 150, e gera embeddings de 768 dimensões via Gemini.
4. O ChromaDB persiste vetores e metadados locais e recupera até três trechos por
   similaridade de cosseno, usando a pergunta e o contexto recente da conversa.
5. O Gemini recebe o histórico recente (até 20 mensagens), os dados comerciais e os
   trechos recuperados. A resposta chega incrementalmente com `st.write_stream`.
   Os trechos ficam disponíveis em um expansor, inclusive no histórico.

O contexto estruturado contém agregações sobre toda a base e rankings limitados,
sem enviar as milhares de linhas e sem geração de SQL pelo LLM. Perguntas sobre dados ausentes devem receber indicação de falta
de informação. A busca retorna os trechos mais próximos, sem garantir relevância;
as citações e conclusões do modelo precisam ser conferidas.

Embeddings já indexados são reutilizados. Alterar documentos ou o modelo de embedding
gera outra coleção, evitando misturar índices incompatíveis. Coleções antigas
permanecem em disco. Para recriar toda a base local, encerre o app e remova somente
`data/runtime/`; os CSVs e documentos originais serão preservados. O chat não é salvo
em disco e pode ser limpo pela barra lateral.

As chamadas enviam dados fictícios, trechos e mensagens à API do Google e podem
consumir cota/créditos. Falhas de chave, rede, cota ou modelo são apresentadas na
interface sem exibir o conteúdo de exceções que possa conter credenciais.

## Estrutura

```text
app.py                       # Interface Streamlit
agro_ai/
  config.py                  # Ambiente e caminhos absolutos
  database.py                # Schema, carga e consultas DuckDB
  schema.py                  # DDL v2 com relações e restrições
  synthetic.py               # Gerador Faker, pandas e numpy
  validation.py              # Validações de integridade e finanças
  gemini.py                  # SDK, embeddings e streaming
  rag.py                     # Chunks, índice persistente e recuperação
  assistant.py               # Contexto comercial e instruções do assistente
data/
  seeds/                     # Oito CSVs + manifest.json com hashes e validações
  backups/                   # CSVs anteriores preservados, ignorados pelo Git
  documents/                 # Política, catálogo e logística fictícios
  runtime/                   # DuckDB e ChromaDB gerados; ignorados pelo Git
scripts/init_data.py         # Inicialização independente do chat
scripts/generate_data.py     # Geração reproduzível com backup
scripts/validate_data.py     # Validação e reconciliação CSV × DuckDB
queries/examples.sql         # Consultas fixas agregadas e limitadas
tests/                       # Testes locais sem chamadas pagas
.env.example                 # Configuração sem segredos
requirements.txt
```

Os nomes dos campos principais foram preservados e as relações agora incluem
pedidos, regiões, centros, estoque e preços mensais. Dinheiro usa `DECIMAL(18,2)`.
Vendas são itens de pedido; receita inclui somente itens faturados. Não somar o
valor dos pedidos ao de suas linhas. Não somar unidades diferentes.

Com a semente padrão `20261015`, receita faturada: **R$ 493.126.517,02**;
carteira pendente: **R$ 155.146.363,54**; cancelado: **R$ 34.784.595,17**.
São valores sintéticos, não resultados de uma cooperativa real.

O app utiliza `data/runtime/cooperativa_v2.duckdb`; o banco legado e os backups
dos CSVs anteriores foram preservados. Os três documentos RAG não foram substituídos.
Seu catálogo e sua vigência didáticos não equivalem ao catálogo sintético ampliado.

Para regenerar, encerre o Streamlit e execute:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_data
.\.venv\Scripts\python.exe -m scripts.init_data
.\.venv\Scripts\python.exe -m scripts.validate_data
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Os testes verificam carga idempotente, receita por status, integridade referencial,
fragmentação, persistência e busca no ChromaDB real com vetores simulados, mudança
de índice após edição de documento, composição de contexto, streaming com SDK
simulado e interface Streamlit sem chave e com chat simulado, incluindo histórico
e limpeza da conversa. Eles não utilizam sua chave nem fazem requisições ao Gemini.
Os bancos de teste são criados em diretórios temporários.

As versões estão fixadas no `requirements.txt`, incluindo Faker para manter a
reprodutibilidade entre execuções. Os testes locais cobrem também volumes,
reprodução exata, finanças, corrupção de dados e limites do contexto. Não chamam
a API real. Consulte o resultado desta ampliação em `docs/base-sintetica.md`.

Validação manual com chave própria: pergunte “Qual a receita faturada por cliente?”,
“Qual o desconto permitido para R$ 18.000?” e “E qual o prazo de entrega?”. Confira
o streaming, os nomes dos documentos, os trechos e a continuidade do histórico.
O botão “Limpar conversa” deve remover todas as mensagens da sessão.

## Diagnosticar erros do chatbot

Os erros agora indicam a etapa e uma referência correspondente ao log no terminal.
Não compartilhe seu `.env`, a chave ou logs de debug do SDK. O logger do projeto
registra apenas metadados seguros, sem texto de conversas ou exceções brutas.

```powershell
# Verificação local de configuração, sem chamar a API:
.\.venv\Scripts\python.exe -m scripts.diagnose
# Opt-in: chamadas reais mínimas e verificação RAG, consumindo cota:
.\.venv\Scripts\python.exe -m scripts.diagnose --live
# Consultar modelos anunciados pela API, sem gerar texto:
.\.venv\Scripts\python.exe -m scripts.diagnose --live --list-models
```

O diagnóstico real retorna código de saída 2 se uma etapa falhar e não repete
requisições automaticamente. `--generation-only`, `--nonstream` e `--model NOME`
permitem comparações pontuais sem alterar o `.env`. Um modelo listado ainda pode
falhar na execução. Variáveis do processo têm precedência sobre o `.env`; reinicie
o servidor para descartar configuração antiga carregada pela versão anterior.

Consulte o [relatório de diagnóstico real](docs/diagnostico-gemini.md): na verificação
de 15/10/2026, RAG real funcionou, mas Gemini 2.5 Flash retornou 404 na geração.
Em uma verificação posterior, Gemini 3.5 Flash respondeu em streaming e o fluxo
completo da pergunta sobre descontos funcionou; esse é o modelo agora configurado.
Os testes locais não comprovam a disponibilidade atual do serviço remoto.

No chatbot, uma geração que recebe HTTP 503 antes de entregar qualquer texto é
repetida uma única vez após 1 segundo. Erros de chave, modelo ou cota e respostas
parciais não são repetidos. Se o serviço continuar indisponível, a interface informa
o erro e preserva a conversa anterior. A repetição pode consumir cota adicional.
O contexto comercial também seleciona as dimensões citadas nas perguntas recentes:
uma pergunta mensal leva totais e 12 meses, sem rankings de clientes/estoque.
Isso reduz conteúdo enviado, mas não garante disponibilidade do Gemini.

## Machine Learning — Etapa 2

Classificador experimental de **backorder** treinado com o dataset público
“Can You Predict Product Backorders?”. A base sintética de estoque tem uma única
fotografia e cenários inseridos por regras: não foi usada para treinar nem avaliar ML.
Veja [dataset, atributos, validação e limitações](docs/ml-etapa2.md).

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.train_ml --download
.\.venv\Scripts\python.exe -m scripts.predict_ml --example
```

O modelo já treinado fica em `models/backorder/model.joblib`; colunas, limiar,
hash e métricas ficam em `models/backorder/metadata.json`. Resultados auditáveis
e matriz de confusão estão em `reports/ml/`. Reexecutar o treino substitui esses
artefatos. O download público é necessário apenas na primeira execução do treino.

No chat, envie:

```text
Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15
```

Essa rota executa o scikit-learn local, sem Gemini; funciona sem chave quando o
artefato está disponível. Perguntas comerciais e RAG continuam no fluxo original.
Valores ausentes não são inventados. A resposta mostra atributos, score e limiar;
o score **não é probabilidade calibrada**. O modelo não foi validado no agro
brasileiro nem para alertas operacionais. Métricas do teste público não são
resultados dos dados sintéticos da cooperativa.

Resultado do teste público reservado (40.000 linhas): accuracy **98,14%**, precision
**16,69%**, recall **43,22%**, F1 **24,08%**, ROC-AUC **0,9359**. O baseline sem
alertas tem accuracy 99,3175% e recall zero; a accuracy isolada não demonstra
qualidade comercial. A suíte local passou com **80 testes**. Consulte a matriz
e as limitações em [ml-etapa2.md](docs/ml-etapa2.md).

## Agentes especializados — Etapa 2

O mesmo chat integra **Agente de Estoque** e **Agente Comercial**, com orquestração
equivalente implementada em Python. O primeiro consulta estoque/pedidos e acessa
o classificador com entradas válidas; o segundo consulta indicadores, recebe pares
produto/centro do primeiro e consulta os documentos via RAG. O Gemini analisa as
evidências e transmite uma única síntese. Veja [arquitetura e validação](docs/agentes-etapa2.md).

Experimente:

- “Quais rupturas de estoque afetam pedidos pendentes e qual o impacto nas margens?”
- “Compare excesso de estoque, faturamento e descontos; consulte a política comercial.”
- Acrescente “e avalie o impacto comercial na carteira e nas margens” ao exemplo ML.

O expansor **Agentes e ferramentas consultadas** mostra o que realmente foi
executado. Ferramentas usam SQL fixo parametrizado, leitura e limites; não há SQL
livre nem comandos destrutivos. Regras de disponibilidade, políticas comerciais e
score ML são distinguidos. Na indisponibilidade do Gemini antes do primeiro texto,
um resumo factual identificado permite consultar os resultados sem inventar análise.

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_agents
# Opt-in para Gemini e RAG reais, consumindo cota:
.\.venv\Scripts\python.exe -m scripts.validate_agents --live
```

Validação desta implementação: **91 testes passaram**, `pip check` sem conflitos
e **três tarefas compostas concluídas com Gemini/RAG reais**, com compartilhamento
de pares e ferramentas registradas em `reports/agents/live_tasks.json`.
O provedor apresentou 503 transitórios recuperados; disponibilidade futura não é garantida.

## Auditoria de rupturas e margem regional

A consulta agora separa **60 posições com disponível zero** (41 com carteira,
**R$ 4.399.084,73**) do grupo amplo de 755 posições sinalizadas
(**R$ 74.151.160,39**, incluindo insuficiência com saldo positivo). Não confundir
esses valores nem tratá-los como perda prevista.

A margem regional consolidada já está disponível nas consultas e nos agentes:
`100 × SUM(receita_liquida - custo_total) / SUM(receita_liquida)`, apenas faturadas.
É margem comercial bruta ponderada, não média simples ou lucro líquido. Veja
[auditoria, resultados e limitações](docs/auditoria-rupturas-margem-regional.md).
Validação: **94 testes aprovados**, `pip check` sem conflitos e as duas perguntas
auditadas executadas com Gemini/RAG reais. Evidências em `reports/audit/`.

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_commercial
```

## Observabilidade Langfuse — Etapa 2

O chat, os dois agentes, DuckDB, Chroma/RAG, ML e Gemini possuem spans opcionais
com latências, ferramentas, status e erros seguros. Configure no `.env`
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` e habilite
`LANGFUSE_ENABLED=true`. A configuração padrão é desativada. Nenhum texto de
conversa ou resultado comercial é exportado; falhas do Langfuse não bloqueiam o chat.
Tokens vêm somente da API; custos não são inventados nem estimados automaticamente.

```powershell
# Cinco perguntas e confirmação via API, quando houver credenciais; consome cota:
.\.venv\Scripts\python.exe -m scripts.validate_observability --live
```

Veja [configuração, privacidade, hierarquia e verificação no painel](docs/observabilidade-etapa2.md).
Nesta execução, as credenciais Langfuse estavam ausentes: **0 traces remotos
enviados/confirmados**. Os testes locais com mocks e SDK em memória não representam
confirmação de ingestão no serviço.
Validação local desta alteração: **114 testes passaram**, `pip check` sem conflitos.

## Avaliação automática — Etapa 2

Há **18 casos golden** e avaliação equivalente ao DeepEval, com juiz LLM para
Faithfulness e Answer Relevancy, além de checks SQL independentes. Streamlit e
avaliador usam a mesma rota funcional. Evidências vêm das ferramentas realmente
executadas; falhas de API ficam separadas de baixa qualidade, sem nota zero inventada.

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_chat --live --interval 15 --max-calls 80
```

O comando começa com dois casos em série e só amplia se funcionarem. A execução
real desta alteração parou no primeiro caso por HTTP 429: **1 pergunta executada,
0 avaliadas pelo juiz, 1 check financeiro aprovado**. Scores permanecem ausentes.
Relatórios em `reports/evaluation/20261017T130820Z/`. Veja
[método, golden, limitações e execução](docs/avaliacao-etapa2.md).
Validação final: **136 testes passaram**, dependências sem conflitos.

A [retomada de dois casos](docs/retomada-avaliacao-dois-casos.md) processou apenas
G01 e G12: Faithfulness 1,000 em ambos; Relevancy 0,667 em G01 e sem nota em
G12 por citação inválida do juiz. Foram 6 chamadas do juiz incluindo diagnóstico,
sem novas gerações Gemini. Os demais 16 casos não foram executados.

A [preparação por lotes](docs/retomada-lotes-etapa2.md) adiciona cache persistente
por resposta/métrica e citações por IDs verificáveis. O novo julgamento apenas
da Relevancy de G12 retornou HTTP 503; nenhuma nota foi atribuída. Os resultados
históricos foram preservados e os 16 restantes estão somente planejados.

```powershell
# Planejamento local, sem chamadas:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches plan --batch-size 2
# Quando solicitado: somente UM próximo lote, respeitando limites e cache:
.\.venv\Scripts\python.exe -m scripts.evaluation_batches run --next --batch-size 2 --live --interval 15 --max-calls 12
```

## Limitações gerais

A [auditoria de observabilidade](docs/auditoria-observabilidade.md) identifica
os HTTP 503/429 do trace de 09:33:29 e documenta a distinção entre resposta
degradada e fallback, avisos de incompletude e resumos de IO sem conteúdo sensível.

Protótipo local acadêmico, sem autenticação, escrita de pedidos ou recomendação
agronômica. Inclui ML experimental público e Langfuse opcional; não inclui CrewAI ou DeepEval.
As consultas atuais retornam agregações e amostras de até 20 linhas; o LLM recebe
rankings de até 10 clientes e 10 alertas, além de agregados limitados. Perguntas
fora desses recortes requerem consultas específicas adicionais. Dados sintéticos
não são evidência de desempenho real de ML; treinamento e avaliação ficam separados.

Referências técnicas: [Gemini — geração de texto](https://ai.google.dev/gemini-api/docs/text-generation),
[Gemini — embeddings](https://ai.google.dev/gemini-api/docs/embeddings) e
[ChromaDB — API Python](https://docs.trychroma.com/reference/python).

## Correção de Faithfulness de G02

O juiz usa IDs de unidades da resposta e de trechos reais recuperados nas novas
avaliações de Faithfulness. Consulte [diagnóstico, protocolo e retomada somente de G02](docs/faithfulness-g02.md).
Resultados históricos e avaliações válidas em cache são preservados; julgamento
inválido continua sem nota.

## Faturamento mensal e completude de G04

O fallback apresenta os meses recuperados do DuckDB. Respostas mensais incompletas
não são reutilizadas pelo cache nem enviadas ao juiz. O histórico com Relevancy
zero permanece preservado. Veja [causa, validações e comando para retestar somente G04](docs/correcao-g04.md).

## Avaliações pendentes em sequência, com cache

Planeje sem chamadas: `python -m scripts.evaluation_pipeline --dry-run`.
O executor separa geração e julgamento, preserva métricas válidas, salva progresso
e aplica orçamento por modelo com reserva para demonstração. Veja
[comando único, retomada e limites locais](docs/avaliacao-sequencial.md).
Execução real exige `--live`; a bateria não é iniciada automaticamente.

Para julgar apenas respostas já armazenadas, use `--dry-run --phase judge` para
planejar e `--live --phase judge` somente quando autorizar as chamadas.
Veja [auditoria das 21 chamadas, reservas por modelo e teto global opcional](docs/auditoria-pipeline-6b67fd.md).

Para selecionar um caso sem executar os demais, use `--cases G06` com
`--phase judge`. Consulte [diagnóstico offline de Faithfulness de G06/G15 e
comandos separados de retomada](docs/faithfulness-g06-g15.md). A auditoria offline
não modifica vereditos nem transforma métricas inválidas em notas.

