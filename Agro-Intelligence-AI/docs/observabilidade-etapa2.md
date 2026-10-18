# Observabilidade — Etapa 2 AI Factory / PUCPR

O módulo `agro_ai/observability.py` integra Langfuse **5.0.2** ao fluxo existente.
Requer Python 3.11+ e Langfuse Cloud ou servidor compatível com SDK v5
(self-hosted 4.59.0+). Referências oficiais:
[migração v5](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v4-to-v5),
[instrumentação](https://langfuse.com/docs/observability/sdk/instrumentation) e
[API Python](https://python.reference.langfuse.com/langfuse).

## Configurar no Windows

Instale as dependências com `./.venv/Scripts/python.exe -m pip install -r requirements.txt`.
No `.env` local, configure as chaves do seu projeto Langfuse e a URL da região
ou servidor correspondente; não publique esse arquivo nem screenshots das chaves.
Os campos vazios abaixo são placeholders:

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=
```

Sem as três configurações ou com `LANGFUSE_ENABLED=false`, o SDK fica desativado.
Variáveis do processo têm prioridade sobre `.env`. O `.env.example` permanece
sem credenciais. Para reiniciar, use Ctrl+C no terminal e:

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Cobertura

Cada pergunta abre `agro.chat.request`, com `agro.chat.question`,
`agro.orchestration.prepare`, agentes `agro.agent.estoque` e/ou
`agro.agent.comercial`, chamadas `agro.agent.tool`, `agro.orchestration.response`
e `agro.chat.response`. Conforme a pergunta, aparecem:

- DuckDB: `agro.duckdb.stock_and_orders`, `commercial_snapshot`,
  `commercial_impact` e `rupture_impact` (todos com prefixo `agro.duckdb.`).
- Chroma: `agro.chroma.synchronize` e `agro.chroma.retrieve`.
- Gemini: `agro.gemini.embeddings` e `agro.gemini.generate`, uma geração por
  tentativa, incluindo eventual retry 503. O span termina após consumir o streaming.
- ML: `agro.ml.predict_backorder`, somente com os sete atributos válidos.
  O caminho ML local também possui orquestração, agente e ferramenta instrumentados.

Nem toda pergunta usa todas as ferramentas. As análises dos agentes e a síntese
compartilham o mesmo trace. Há latências, status, nome do agente/ferramenta,
tentativa e categorias/códigos HTTP seguros. Fallback factual e entradas ML
insuficientes são identificados; falhas intermediárias ficam visíveis nos filhos.

## Privacidade e falhas

Os campos Input/Output do root agora contêm apenas objetos estruturados com
`content=omitted_for_privacy`, tamanho e status; nenhum texto de conversa.
`degraded` identifica síntese gerada com etapa intermediária indisponível;
`fallback` identifica substituição pelo resumo factual. Veja a
[auditoria do trace de 09:33:29](auditoria-observabilidade.md).

Não são enviados textos de pergunta, resposta, histórico, prompts de sistema,
trechos RAG, SQL, resultados comerciais, identificadores de clientes, valores de
entrada ML, mensagens brutas de exceção ou stack traces. São enviados apenas
metadados permitidos e comprimentos. Não há IDs persistentes de usuário ou sessão.
Um provider OpenTelemetry privado evita exportar spans automáticos de terceiros.
O SDK recebe a finalização sem o objeto de exceção, evitando captura automática.

Tokens são registrados apenas quando presentes no `usage_metadata` do Gemini.
Snapshots cumulativos substituem o anterior; não são somados. Ausência de informação
continua desconhecida, sem zeros inventados. Não são enviados custos: a API usada
não informa custo faturado. O modelo fica somente em metadados, sem o campo de
precificação automática `model`, evitando apresentar estimativas como cobrança real.

Inicialização, atualização, finalização e flush falhos não interrompem o chat.
Logs de observabilidade usam mensagens genéricas; logs internos de exportação são
suprimidos para evitar vazamento de payloads. Cada pergunta agenda flush em thread
daemon; o validador espera até cinco segundos. Falha de rede pode perder eventos.
Flush concluído significa tentativa de esvaziamento, não prova de ingestão.
Não há armazenamento local persistente para reenvio garantido.

## Verificar cinco traces

O comando abaixo autoriza cinco perguntas fixas de demonstração, chamadas Gemini,
embeddings e envio ao Langfuse, podendo consumir cota. Só executa quando as
credenciais necessárias estão configuradas e a autenticação Langfuse responde:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_observability --live
```

Ele cobre faturamento/margem regional, rupturas, política de descontos, tarefa
composta estoque/comercial e tarefa composta com sete entradas ML explícitas.
O relatório seguro fica em `reports/observability/validation.json`: separa perguntas
executadas, traces criados, flush e traces completos confirmados pelo servidor.
Consulta a API v5 `observations.get_many` sem input/output, verificando IDs,
hierarquia, nomes esperados e finalização; repete a consulta após atraso de ingestão.
Um servidor lento pode exigir nova verificação no painel. Paginação acima de
100 observações não é coberta por esse pequeno validador.

Abra o projeto correspondente no painel Langfuse e procure os IDs do relatório
ou `agro.chat.request`. Expanda os filhos e confira latências, ferramentas,
status e tokens disponíveis. A confirmação via API não equivale a inspeção visual.
Sem `--live`, nenhuma pergunta ou envio remoto é executado.

### Diagnóstico de autenticação

O validador registra `authentication.category` sem mensagens brutas: autenticação
(HTTP 401/403), configuração (400/404), cota (429), serviço (5xx), timeout,
rede ou permissão de rede. Não confundir bloqueio local com chave inválida.
O SDK instalado 5.0.2 suporta `LANGFUSE_BASE_URL` e o argumento `base_url`;
não é necessário substituir por `LANGFUSE_HOST`.

Na verificação posterior à configuração das credenciais, as quatro variáveis foram
carregadas e `auth_check()` retornou **true** com rede autorizada. Dentro do sandbox,
o mesmo teste produziu `ConnectError` causado por `PermissionError`. A causa
comprovada nessa execução foi restrição de rede do ambiente de execução.
Resultado sanitizado em `reports/observability/auth_diagnostic.json`.
Autenticação bem-sucedida não confirma envio de traces nem funcionamento Gemini.

## Evidência desta alteração

Credenciais Langfuse ausentes no ambiente inspecionado: **zero chamadas reais de
validação, zero traces enviados por esta execução e zero confirmados no servidor
ou visualmente**. Não se afirma que a integração remota foi validada.

Os testes incluem cinco perguntas completas com DuckDB/modelo locais e provedor
Gemini/RAG simulados, árvore de spans, privacidade, tokens cumulativos, ausência
de uso/custo inventado, retry, falhas do SDK e flush com espera limitada. Outro
teste usa o SDK Langfuse real com exporter OpenTelemetry em memória, sem rede.
O readback v5 também é testado com mocks, incluindo árvores incompletas.
Resultado final: **114 testes aprovados** e `pip check` sem conflitos.

Arquivos envolvidos: `agro_ai/observability.py`, `app.py`, `agro_ai/gemini.py`,
`agro_ai/database.py`, `agro_ai/rag.py`, `agro_ai/ml/inference.py`,
`agro_ai/agents/tools.py`, `agro_ai/agents/orchestrator.py`,
`scripts/validate_observability.py`, `tests/test_observability.py`,
`requirements.txt`, `.env.example`, `README.md`, esta documentação e
`reports/observability/validation.json`. O `.env` com segredos não foi alterado.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Esta alteração não inclui DeepEval. Os dados sintéticos não constituem avaliação
de desempenho de ML; o treinamento público existente permanece separado.
