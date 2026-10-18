# Modelos Gemini e limites — auditoria de 17/10/2026

## Evidência e atribuição do consumo

Foi consultado `client.models.list()` com a chave configurada, sem imprimi-la.
O retorno sanitizado está em `reports/models/available.json`. A API listou,
entre outros, `models/gemini-3.1-flash-lite`, `models/gemini-3.6-flash`,
`models/gemini-3.5-flash` e `models/gemini-embedding-001`. Os três primeiros
anunciam `generateContent`; o último anuncia `embedContent`.

Antes da alteração, o `.env` tinha `GEMINI_MODEL=gemini-3.5-flash` e
`GEMINI_EMBEDDING_MODEL=gemini-embedding-001`, sem variáveis para agente/juiz.
O modelo principal alimentava tanto as análises dos agentes como a síntese e
o juiz. RAG gerava vetores com embedding-001 e usava o principal para redação;
Chroma e DuckDB não executam modelos Gemini próprios. ML usa o artefato
scikit-learn, não o Gemini.

**Não foi encontrado componente configurado explicitamente para 3.6 Flash**.
Os traces históricos auditados também identificavam solicitações a 3.5 Flash.
A disponibilidade do 3.6 na listagem não significa que ele foi chamado.
O painel de consumo informado pelo usuário não permite identificar a origem
das chamadas, nem provar que 3.5 é um alias para 3.6. Não se presume isso.
Novas gerações registram `model_name` solicitado e `model_version` retornado
pela API quando disponível, com filtros de formato para não exportar texto livre.

## Configuração final

| Componente | Variável | Valor efetivo no `.env` |
|---|---|---|
| Síntese final / modelo principal | `GEMINI_MODEL` | `gemini-3.5-flash` |
| Análises de estoque e comercial | `GEMINI_AGENT_MODEL` | `gemini-3.1-flash-lite` |
| Avaliador Faithfulness / Relevancy | `GEMINI_JUDGE_MODEL` | `gemini-3.1-flash-lite` |
| RAG: consulta e indexação de vetores | `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` |
| Intervalo por modelo | `GEMINI_MIN_INTERVAL_SECONDS` | `15` |

Defaults do código: principal `gemini-3.5-flash`, embedding `gemini-embedding-001`,
intervalo 15s. Se `GEMINI_AGENT_MODEL` estiver ausente, herda o principal; se
`GEMINI_JUDGE_MODEL` estiver ausente, herda o agente. Isso mantém configurações
antigas compatíveis. O `.env.example` recomenda explicitamente Lite para ambos.
Variáveis do processo têm precedência sobre `.env`; um terminal com valor antigo
exportado pode continuar usando esse valor. A chave e o embedding não mudaram.

Os dois agentes mantêm as mesmas ferramentas e evidências. Usam um gateway
Lite separado para análise; a síntese continua usando o gateway principal.
Os gateways são reutilizados sequencialmente na tarefa. Não existe troca
automática de modelo após erro de limite e não foram alterados faturamento ou chaves.

## Compatibilidade verificada

Foi escolhido o ID estável **exatamente como listado pela API**,
`gemini-3.1-flash-lite`, em vez de deduzir um ID pelo nome do painel ou usar
aliases `latest`. A [documentação oficial do modelo](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
confirma geração textual e saída estruturada, necessárias para agentes e juiz.

Executou-se **uma única geração mínima**, com streaming e schema JSON `{ok:bool}`.
O JSON foi validado e `model_version` retornou `gemini-3.1-flash-lite`.
Resultado em `reports/models/configuration.json`. Não houve repetição nem
geração no 3.6. Esse teste confirma acesso e compatibilidade técnica naquele
momento; não mede qualidade do juiz, qualidade comercial ou saldo futuro de cota.

O índice Chroma existente foi inspecionado sem reindexar: coleção
`comercial-dfcbe9f7e20159a1133bf09d`, **3 trechos**, **768 dimensões**,
`gemini-embedding-001`. A identificação depende do embedding, dimensões e
conteúdo dos documentos, não do modelo de geração. Não houve nova chamada de
embedding nem alteração de documentos, banco comercial ou modelo ML.

## Controle de limites

`agro_ai/api_limits.py` serializa requisições do processo, inclusive todo o
streaming, e impõe o intervalo por modelo. Abrange agentes, síntese, embedding,
juiz e diagnóstico. A bateria de avaliação mantém concorrência 1 e orçamento
explícito; sua limitação anterior permanece ativa.

O SDK usa `attempts=1`. O adaptador só repete uma vez 503 antes de qualquer texto
e **sem Retry-After**. Com Retry-After, registra pausa persistente e devolve o
erro; não faz retry imediato. Aceita segundos, data HTTP e RetryInfo estruturado.
Em 429, não repete; pausa pelo menos 60s ou o tempo maior informado.

Um limite diário só é identificado automaticamente por metadados estruturados
de QuotaFailure com `quotaId`/`quotaMetric` diário. O bloqueio persiste até o
próximo reset. Conforme a [documentação oficial de limites](https://ai.google.dev/gemini-api/docs/rate-limits),
RPD reinicia à meia-noite no horário do Pacífico. O código trata o fuso e DST.
Um 429 sem esse detalhe não é rotulado como cota diária por suposição.

O relato do usuário de **24/20 RPD no 3.6** foi usado para bloquear localmente
esse modelo até o próximo reset, sem testá-lo. Os limites relatados de 15 RPM/
500 RPD no Lite não são considerados contagem de saldo: a listagem de modelos
não informa consumo restante. O teste mínimo Lite funcionou; nenhuma bateria
de 18 casos foi reexecutada nesta alteração.

Estado fica em `data/runtime/api_limits/`, ignorado pelo Git, com namespace
derivado da chave, sem chave, prompts, respostas ou corpo HTTP. Trocar de chave
não é estratégia de recuperação: os limites do provedor são por projeto.
Não há contagem global de TPM/RPD da conta, pois outros aplicativos também
consomem cota. Serialização é por processo; não execute múltiplos Streamlits ou
CLI de avaliação simultâneos. Bloqueios persistidos são compartilhados pelos
processos com a mesma configuração, mas não há coordenador distribuído.

Falhas continuam ERROR nos spans, com categoria segura para limite diário ou
cooldown quando houver evidência. Fallback e ML local permanecem disponíveis;
o modelo principal preservado ainda pode apresentar seus próprios limites.
Os custos não foram estimados e nenhuma promessa de economia percentual é feita.

## Executar e conferir no Windows

Reinicie o Streamlit após atualizar `.env` (Ctrl+C e o comando abaixo):

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m streamlit run app.py
# Configuração e índice locais, sem geração:
.\.venv\Scripts\python.exe -m scripts.check_models
# Listagem oficial da API, sem geração:
.\.venv\Scripts\python.exe -m scripts.diagnose --live --list-models
# Opcional, somente com cota: UMA prova mínima de streaming/JSON:
.\.venv\Scripts\python.exe -m scripts.check_models --probe
.\.venv\Scripts\python.exe -m pytest -q
```

Arquivos alterados: `config.py`, `gemini.py`, `agents/orchestrator.py`,
`evaluation/judge.py`, `evaluation/runner.py`, `diagnostics.py`, `observability.py`,
`app.py`, `.env` (somente campos de configuração), `.env.example`,
`scripts/diagnose.py`, `tests/conftest.py` e README. Criados: `api_limits.py`,
`scripts/check_models.py`, `tests/test_models_limits.py`, esta documentação e
relatórios em `reports/models/`. Nenhuma credencial foi incluída em relatórios.

Resultado: **146 testes passaram** na suíte completa; `pip check` sem conflitos.
Os testes novos cobrem configuração e precedência, escolha do agente/juiz,
Retry-After (segundos/data HTTP), RetryInfo, evidência diária estruturada,
reset no fuso do Pacífico, bloqueio persistente, espaçamento e ausência de
retry imediato de 503 com Retry-After. A prova mínima real passou uma vez;
não se reexecutou a bateria de avaliação nem se testou geração no principal.
