# Auditoria de observabilidade — 17/10/2026

Fonte: consulta autenticada, somente leitura, da API Langfuse v5 dos cinco
traces em `reports/observability/validation.json`. Evidências sanitizadas em
`reports/observability/audit.json`. Não foram feitas novas chamadas Gemini.

## Causa comprovada

Trace `05d850d53c649d6b63c95cf8349e33fd`, início 12:33:29.286 UTC
(09:33:29.286 em São Paulo), duração **32,571 s**:

| Etapa | Resultado | Duração | Tokens total da API |
|---|---|---:|---:|
| Análise estoque, tentativa 1 | HTTP 503 / ERROR | 5,322 s | desconhecido |
| Espera de retry | espera programada | 1 s | não aplicável |
| Análise estoque, tentativa 2 | sucesso | 9,995 s | 4.521 |
| Análise comercial | HTTP 429 / ERROR | 0,535 s | desconhecido |
| Síntese final | sucesso | 13,241 s | 9.042 |

Os HTTP são evidência direta dos spans. Não há evidência de timeout. O 429
não permite determinar se o limite foi por minuto, dia, tokens ou outra
restrição: detalhes brutos não foram armazenados por privacidade. Não é possível
afirmar esgotamento de cota ou problema de faturamento. Não há arquivo de log
persistente no projeto que acrescente detalhes. Os logs de terminal fornecidos
na conversa são coerentes com os códigos preservados.

O root estava WARNING/fallback porque o validador classificava qualquer falha
intermediária como fallback. A síntese final da quinta pergunta funcionou;
**não foi substituída pelo resumo factual**. Corrigido: `degraded` para síntese
com análise/ferramenta ausente; `fallback` somente para resumo factual. Streamlit
e validador agora usam a mesma classificação considerando todas as ferramentas.

## Tokens e chamadas

Total recebido da API nas duas gerações bem-sucedidas: **13.563**,
sendo input 9.324, output 1.012 e reasoning 3.227. Uso das falhas permanece
desconhecido. Não é uma medição completa do consumo/custo da conta. Não há custos
reportados nos spans consultados; o aplicativo não envia estimativas. O modelo
fica em metadados, sem ativar precificação automática. Snapshots cumulativos
de streaming substituem o anterior, sem somar a mesma contagem repetidamente.

O fluxo composto mantém duas análises especializadas e uma síntese. Com o retry,
houve quatro tentativas. O SDK usa `attempts=1`; o adaptador só repete uma vez
HTTP 503 antes de qualquer texto, após um segundo. Não repete 429, timeout ou
resposta parcial. O timeout de 30 segundos não foi alterado.

Foi comprovada repetição de todo o estoque no prompt da análise comercial:
agora cada agente recebe suas próprias evidências. Os resultados compartilhados
continuam em `impacto_compartilhado`, e a síntese recebe as evidências dos dois
agentes. JSON usa separadores compactos. A economia real após a mudança ainda
não foi medida com a API; não são prometidos percentuais de redução.

## Precisão, privacidade e erros

O fallback usa somente resultados efetivos das ferramentas, distinguindo
saldo zero/insuficiência, amostra/total, carteira/faturamento e score ML/
probabilidade. Testes conferem totais de carteira em ruptura e faturamento.
Sínteses LLM ainda requerem conferência humana; não se garante ausência de erros.

Agora há aviso determinístico quando falta análise ou ferramenta, mesmo com
síntese final bem-sucedida. Quando a síntese falha, o resumo factual fica
identificado. Falha após entrega parcial continua propagada ao Streamlit,
que descarta a resposta e não a salva no histórico. O bloqueio de alegações
enganosas de probabilidade ML permanece ativo.

Input/Output eram undefined porque nenhum conteúdo era exportado. Os novos
roots recebem somente objetos como
`{"content":"omitted_for_privacy","characters":174}` e status no output.
Não são a pergunta/resposta original nem resumo semântico delas. Não se exporta
texto bruto; os traces históricos não são reescritos.

Nos cinco traces, todos os vínculos de pai estavam presentes. O ML aparece
somente na quinta pergunta, com sete entradas explícitas. DuckDB e Chroma ficam
abaixo das ferramentas/agentes, e geração abaixo da chamada correspondente.
Falhas de geração continuam ERROR, inclusive o 503 recuperado. Pais afetados
passam a WARNING/degraded. Tokens não são copiados para os pais.

## Arquivos e testes

Alterados: `agro_ai/observability.py`, `agro_ai/agents/orchestrator.py`, `app.py`,
`scripts/validate_observability.py`, `tests/test_agents.py`,
`tests/test_observability.py`, `docs/observabilidade-etapa2.md` e `README.md`.
Criados: `scripts/audit_observability.py`, `tests/conftest.py`, esta documentação
e `reports/observability/audit.json`.

O fixture dos testes desabilita exportação remota, evitando misturar simulações
com traces reais quando o `.env` está preenchido. Testes de telemetria usam
mocks ou SDK real com exporter em memória. A auditoria é somente leitura.

Resultado: **124 testes aprovados**; `pip check` sem conflitos. Incluem
classificação degraded/fallback, IO redigido, preservação de spans ERROR,
aviso obrigatório de análise ausente, fallback com totais reais do DuckDB,
streaming parcial, retry, tokens cumulativos, ML e cinco fluxos simulados.
As mudanças novas foram validadas localmente, sem nova geração Gemini nem
confirmação visual de novos traces no painel.

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_observability
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```
