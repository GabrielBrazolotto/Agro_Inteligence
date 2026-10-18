# Auditoria local da execução 20261018T125121Z-pipeline-6b67fd

## O que aconteceu

O ledger registra 21 tentativas, todas de geração/recuperação, sem julgamento:

| Modelo | Tentativas | Falhas | Teto local diário | Reserva | Limite para avaliação |
|---|---:|---:|---:|---:|---:|
| gemini-3.5-flash | 8 | 2 (HTTP 503) | 20 | 5 | 15 |
| gemini-3.1-flash-lite | 7 | 1 (timeout) | 20 | 5 | 15 |
| gemini-embedding-001 | 6 | 0 | 20 | 5 | 15 |

O contador persistente confere: 8, 7 e 6. **Não ocorreu ultrapassagem do limite
por modelo.** `--daily-limit 20` sempre significou 20 por modelo; não era teto
global de 20 para a soma. O limite de sessão era 100, portanto admitia 21.
As duas tentativas HTTP 503 foram seguidas do retry único permitido e contado
separadamente (G06 e G10). Falhas, timeout e embeddings consumiram orçamento local.

O `stop_reason=api_failure_or_limit` é um rótulo genérico. Em G10, o agente de
estoque teve timeout em `gemini_analise` (referência `03a2191d3454`). A análise
comercial terminou. A síntese principal teve HTTP 503, repetiu e terminou com
sucesso. O pipeline parou ao concluir G10 porque havia falha de ferramenta,
preservando a resposta degradada com aviso. **Não existe HTTP 429 nesse ledger**;
não há evidência de cota esgotada nessa execução.

## Respostas realmente salvas

Todas possuem integridade de cache válida, pergunta correspondente, fingerprints
atuais das fontes e evidências originais preservadas. São elegíveis para julgamento:

| Caso | Situação | Conferência local |
|---|---|---|
| G04 | Fallback factual completo | 12 meses e valores exatos; oráculo mensal aprovado |
| G06 | Resposta Gemini concluída | Margem R$ 100.023.056,21; oráculo aprovado |
| G07 | Resposta Gemini concluída | Regra de aprovação de desconto de 7%; documento recuperado |
| G08 | Resposta Gemini concluída | Desconto à vista de 2%, não cumulativo; documento recuperado |
| G09 | Resposta Gemini concluída | Desconto de 9% não permitido; documento recuperado |
| G10 | Resposta Gemini degradada | Carteira de ruptura R$ 4.399.084,73; oráculo aprovado; aviso do timeout mantido |

G04 usou o fallback corrigido porque a síntese foi rejeitada pela proteção de
completude mensal, não por falha da API. A série completa realmente consta no cache.
O fallback contém também documentos/totais que poderão afetar relevância; não foi
reescrito para melhorar nota. G10 tem evidência das duas áreas e síntese salva,
mas a análise do agente de estoque ficou indisponível. Essa limitação permanece
explícita e não impede julgar a resposta existente.

Elegibilidade para reutilização **não equivale a aprovação de qualidade pelo juiz**.
As 12 métricas (duas por caso) continuam pendentes e sem nota inventada.
G01, G02, G03, G05 e G12 permanecem completos. G11 e G13–G18 não possuem resposta;
o modo de julgamento os ignora sem executar agentes.

## Ajustes comprovados e proteção antes do envio

- Corrigido o dry-run: antes ignorava `--phase judge` e estimava geração para
  casos sem resposta. Agora lista somente as seis respostas armazenadas,
  informa os sete casos ignorados e estima **seis chamadas ao juiz**, sem agentes
  nem embeddings. As duas métricas são pedidas juntas por caso.
- O orçamento já era debitado e gravado atomicamente em `acquire` antes de cada
  função SDK. Agora o ledger também é checkpointado antes do despacho, com ID
  da admissão, modelo e indicação `debited_before_dispatch`; a reserva de tokens
  é identificada como estimativa local, separada do uso confiável retornado pela API.
- Validado que o modelo efetivo da chamada corresponde ao orçamento debitado.
  Divergência bloqueia a chamada. O teste de limite confirma que a 16ª chamada
  ao mesmo modelo não é enviada quando o orçamento de avaliação é 15.
- Adicionado teto **global opcional**, independente dos tetos por modelo:
  `--total-daily-limit` e `--total-reserve-demo`. O total considera os débitos
  diários já persistidos de todos os modelos, inclusive tentativas anteriores.
  Ele não começa do zero na retomada. O mais restritivo dos controles prevalece.
- Dry-run mostra consumo diário local registrado, saldo de avaliação por modelo,
  bloqueios persistidos e teto global opcional. Não consulta a cota do provedor.

Exemplo para planejar um teto global de 20 com reserva global de cinco:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --dry-run --phase judge --daily-limit 20 --reserve-demo 5 --total-daily-limit 20 --total-reserve-demo 5
```

No estado auditado, 21 tentativas já foram debitadas no dia. Esse teto global
exibirá saldo **zero** e bloqueará novas chamadas até o reset. Não se deve apagar
o contador para liberar orçamento. O teto global não era parte da configuração
da execução original e não pode ser aplicado retroativamente.

## Retomada segura apenas do juiz

Planejamento sem qualquer chamada:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --dry-run --phase judge --daily-limit 20 --reserve-demo 5 --max-calls 6
```

Quando houver autorização e cota real disponível:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --phase judge --interval 15 --daily-limit 20 --reserve-demo 5 --max-calls 6
```

No estado observado o Lite tem 7 débitos do dia, restando 8 requisições para
avaliação dentro do teto local de 15. As seis chamadas planejadas cabem nesse
saldo local. Isso **não comprova cota efetiva disponível** no Google, pois o
contador não conhece uso externo ou outros scripts anteriores. HTTP 429,
Retry-After e bloqueios diários continuam sendo respeitados. Não houve teste real
de acesso nem julgamento nesta alteração.

Execute o mesmo comando para retomar caso haja interrupção. Métricas válidas
salvas não são refeitas; julgamentos inválidos permanecem sem nota. Não usar
`--phase all` se a intenção for julgar somente essas seis respostas.

## Arquivos e verificações

Alterados `agro_ai/evaluation/budget.py`, `agro_ai/evaluation/pipeline.py`,
`scripts/evaluation_pipeline.py`, `tests/test_evaluation_pipeline.py`, README
e documentação. Não se alteraram dados, documentos RAG, respostas nem notas.
O manifesto `reports/evaluation/pipeline-6b67fd-before-audit.json` permite conferir
hashes do relatório original, cache e contadores locais antes/depois.

Os testes reproduzem as 21 chamadas distribuídas sem ultrapassagem por modelo,
bloqueio da 16ª chamada, teto global com reserva e persistência, débito/checkpoint
antes do SDK, retries/falhas/embeddings, IDs de modelos e planejamento judge-only.

Resultado local: **200 testes aprovados em 43,14 s**; `pip check` sem incompatibilidades.
Foram executados somente testes locais e dry-runs; novas chamadas Gemini: **zero**.
Conferência SHA-256 de **66 arquivos** do relatório original, cache e contadores:
nenhuma alteração. O relatório local complementar está em
`reports/evaluation/20261018T130353Z-audit-6b67fd-850092/`, com
`judge-dry-run.json`, `response-audit.json` e consolidado dos 18 casos.
