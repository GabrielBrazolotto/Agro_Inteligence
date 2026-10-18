# Agentes especializados — AI Factory / PUCPR

## Arquitetura escolhida

Solução equivalente a uma orquestração multiagente em Python, sem acrescentar
CrewAI: `StockAgent` e `CommercialAgent` têm papéis, planejamento limitado ao domínio,
ferramentas próprias e evidências separadas. O `AgentOrchestrator` identifica os
domínios solicitados, executa os agentes necessários, compartilha resultados em
`WorkState` e transmite uma única síntese em português pelo Gemini. A solução
usa as dependências existentes; `requirements.txt` documenta essa escolha.

Não é autonomia irrestrita, nem agentes com acesso livre a código ou SQL. O
roteamento e o conjunto de ferramentas são explícitos; cada agente interpreta as
evidências por uma chamada Gemini quando disponível. Em uma tarefa composta há
até duas análises e uma síntese, além dos embeddings do RAG. Isso pode consumir
mais cota e levar mais tempo que uma pergunta simples. O mecanismo existente de
uma repetição em 503 antes de receber texto permanece no adaptador Gemini.

Antes da implementação foram inspecionados app, assistente, consultas, RAG e ML;
a suíte anterior passou com **80 testes**. O classificador, seus atributos, artefato,
documentos RAG e CSVs comerciais não foram alterados.

## Agente de estoque

- `duckdb_estoque_pedidos`: consulta a fotografia de estoque e agrega itens de
  pedidos pendentes por produto/centro. Sinaliza disponível zero ou quantidade de
  carteira maior que disponível, sempre comparando a mesma unidade no mesmo par.
- Retorna totais completos e até 20 pares prioritários por valor de carteira.
- `scikit_learn_backorder`: valida os sete atributos explícitos e chama o pipeline
  já treinado. Sem valores válidos, retorna pedido de informação, sem executar ML.

As regras de saldo/carteira são descrições da fotografia de 30/09/2026 e dos pedidos,
não previsões estatísticas. A fotografia não tem conciliação cronológica com
movimentos: não prova descumprimento de um pedido. Carteira associada não é perda
estimada. O score ML é de um classificador público externo não calibrado e não
validado na cooperativa; os atributos fornecidos não são associados automaticamente
a um produto da base. Não há modelo adicional de previsão futura de demanda.

## Agente comercial

- `duckdb_comercial`: usa as consultas fixas existentes para faturamento, descontos,
  margem, regiões, famílias e carteira. Exclui dados brutos em massa do contexto.
- `duckdb_impacto_pares`: recebe os pares identificados pelo agente de estoque e
  consulta carteira e margem desses mesmos pares, por família. Essa amostra não
  representa o total global. Valores de pedidos não são somados novamente aos itens.
- `chroma_rag_comercial`: sincroniza o índice e usa a recuperação semântica existente,
  com embeddings Gemini, para consultar documentos e preservar suas citações.

Os resultados do agente de estoque são disponibilizados antes da análise comercial.
O coordenador recebe evidências dos dois agentes e suas análises. Assim, a colaboração
inclui uma consulta dependente dos resultados reais anteriores, não apenas dois
textos sobre o mesmo prompt. O contexto informa que documentos didáticos têm escopo
próprio e não tornam descontos sintéticos anômalos uma política autorizada.

## Chat, continuidade e rastreabilidade

O chat mantém mensagens, fontes e registro de ferramentas por resposta. O expansor
**Agentes e ferramentas consultadas** informa agente, ferramenta, estado e, quando
aplicável, dependência/erro/referência. Esse registro corresponde às chamadas
executadas pelo programa, não a ferramentas declaradas pelo LLM.

Perguntas curtas iniciadas por “E ...” ou “Quanto a ...” usam as perguntas recentes
para preservar o domínio. O roteamento por palavras-chave pode exigir reformulação
em pedidos ambíguos. A rota simples de previsão ML já existente foi preservada;
pedidos que combinam ML e impacto comercial passam pelos dois agentes.

Se Gemini falhar antes de entregar texto, a aplicação fornece **resumo factual das
ferramentas**, claramente identificado como sem síntese do Gemini. Não se apresenta
esse resumo como análise do LLM. Se houver falha após texto parcial, a tentativa
é descartada e o tratamento anterior de erro/histórico permanece. Falhas de RAG ou
ML ficam registradas; os demais resultados podem continuar, sem inventar a parte
que faltou. Nenhum erro bruto ou segredo é exibido.

Em tarefas compostas com previsão ML, a síntese é retida até uma verificação
conservadora de linguagem: afirmações como “indica a probabilidade de falta” são
rejeitadas e substituídas pelo resumo factual com score/limiar reais. O registro
fica `rejected`, com motivo `uncalibrated_ml_probability_claim`. A barreira é
heurística, não uma garantia de correção semântica de toda resposta. Demais tarefas
preservam streaming; a rota ML simples já informa score não calibrado localmente.

## Segurança

Todas as conexões de ferramentas são DuckDB `read_only=True`. Não há ferramenta
de execução SQL livre, shell, escrita, exclusão ou alteração de esquema. Consultas
são constantes, retornam agregações e têm `LIMIT 20`. Os pares compartilhados são
validados como inteiros positivos, deduplicados, limitados a 20 e passam como
parâmetros SQL. Apenas a lista de placeholders é construída pelo programa.

Documentos e saídas de ferramentas são tratados como evidências, não instruções.
Gemini não tem canal para executar comandos. Logs técnicos usam nomes de ferramentas,
estado e referências, sem chave, prompt ou exceção bruta. O relatório de validação
contém somente as três tarefas didáticas, dados sintéticos e resultados públicos
do ML; não armazena conversas de uso normal.

## Executar validações

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m pytest -q
# DuckDB e ML reais; sem LLM/embeddings. RAG fica indisponível de forma explícita.
.\.venv\Scripts\python.exe -m scripts.validate_agents
# Com chave configurada: Gemini e Chroma/embeddings reais; consome cota.
.\.venv\Scripts\python.exe -m scripts.validate_agents --live
```

Evidências: `reports/agents/local_tasks.json` e `reports/agents/live_tasks.json`.
Contêm plano, chamadas, dependências, evidências e resposta final. O modo local não
é prova de funcionamento do Gemini ou da recuperação semântica. Os testes usam
também um índice simulado com texto do documento real para validar a coordenação,
e um gateway simulado para verificar as três etapas de análise/síntese.

Tarefas compostas executadas pelo script:

1. Quais rupturas afetam pedidos pendentes e qual o impacto comercial nas margens?
2. Compare excesso de estoque, faturamento e descontos; consulte a política comercial.
3. Preveja backorder com os sete atributos explícitos e avalie carteira e margens.

A terceira tarefa usa o exemplo `estoque=10; prazo=8; transito=0; previsao_3m=100;
vendas_1m=20; vendas_3m=60; estoque_minimo=15`. O score é calculado pelo artefato ML,
sem dedução de atributos a partir do DuckDB.

## Resultados locais verificados

- Suíte completa: **91 testes aprovados**; `pip check` sem incompatibilidades.
- Três tarefas compostas executadas também com **Gemini e RAG reais** após as
  correções finais. Em todas, as ferramentas, as duas análises especializadas e
  a síntese concluíram com estado `ok`; o comercial consultou os 20 pares
  compartilhados. Ocorreram erros transitórios 503 recuperados pela repetição
  existente. Isso comprova as execuções registradas, não disponibilidade futura.
- Três tarefas locais executadas com DuckDB e artefato scikit-learn reais. Nesse
  modo o RAG indisponível foi explicitamente registrado, não simulado como sucesso.
- Nas tarefas, o estoque encontrou 60 posições com disponível zero, 60 em excesso
  e 755 pares sinalizados pela regra declarada. Carteira associada a esses pares:
  **R$ 74.151.160,39**, sem inferir que seja perda ou previsão futura.
- O comercial recebeu os 20 pares priorizados e reconciliou **R$ 9.339.600,56**
  de carteira nessa amostra, sem duplicação de linhas e sem extrapolação ao total.
- A tarefa ML executou o pipeline com os sete atributos explícitos: score
  **0,9266898444**, limiar **0,91**, classe 1. Não é probabilidade calibrada.
- Os testes incluem SQL malicioso como texto, pares inválidos/excesso de limite,
  prevenção de inferência com atributos ausentes, compartilhamento das evidências,
  falha 503 com fallback identificado, rejeição de linguagem probabilística indevida
  e persistência do registro de ferramentas no histórico Streamlit.

Langfuse e DeepEval não foram implementados. O modelo e suas métricas não foram
retreinados; scores de inferência foram executados nas tarefas que informam os sete atributos.
