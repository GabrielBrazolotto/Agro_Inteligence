# Avaliação sequencial com retomada — Etapa 2

## Estado confirmado localmente

G01, G02, G03, G05 e G12 estão completos e são preservados. Existem 13 casos
pendentes: G04, G06–G11 e G13–G18. A resposta antiga incompleta de G04 é inelegível
para reutilização; o histórico com Relevancy zero não é alterado. Após uma nova
resposta completa de G04, as próximas retomadas a reutilizam normalmente.
Não há uma opção que force repetidamente a geração de G04 ou dos casos concluídos.

## Comando único e retomada

Inspeção sem rede, sem criar SDK e sem gravar cache, orçamento ou relatórios:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --dry-run --interval 15 --daily-limit 20 --reserve-demo 5
```

Depois de autorizar as chamadas reais, executar todos os pendentes:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --interval 15 --daily-limit 20 --reserve-demo 5 --max-calls 100
```

Pode interromper com `Ctrl+C`. Execute **o mesmo comando** para retomar: a fila é
recalculada pelo cache, sem voltar à geração das respostas já disponíveis nem ao
julgamento das métricas já válidas. Se ainda houver cooldown ou limite diário,
o executor não fará novas chamadas ao modelo bloqueado. Não há espera automática
durante a madrugada, troca de modelos/chaves nem alteração de faturamento.

## Fases e economia

O padrão `--phase all` executa duas fases independentes: gera e salva as respostas
pendentes; em seguida julga as respostas armazenadas, usando suas próprias evidências.
Antes de **cada** caso verifica novamente resposta, estado das fontes e métricas.
As duas métricas ausentes são pedidas em uma única chamada ao juiz. Se apenas uma
estiver pendente, só essa métrica é solicitada. Métricas baixas válidas permanecem
válidas; não se repetem avaliações para aumentar notas.

As fases também podem ser executadas separadamente:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --phase generate --interval 15 --reserve-demo 5
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --live --phase judge --interval 15 --reserve-demo 5
```

A fase judge não gera respostas ausentes. Respostas/contextos e métricas são
armazenados em arquivos separados, imutáveis, no cache persistente existente.
G04 só aceita série mensal completa com valores recuperados; resposta nova
incompleta não é julgada. Uma avaliação inválida é registrada sem nota e não
é repetida em loop. Pode ser retomada em outra execução após análise do motivo.

## Limites por modelo

Auditoria da execução com 21 chamadas: [contagem por modelo e retomada de seis
julgamentos armazenados](auditoria-pipeline-6b67fd.md). `--phase judge` também é
respeitado pelo dry-run. Para um teto adicional somando todos os modelos, use
`--total-daily-limit` e, se necessário, `--total-reserve-demo`; ambos são opcionais
e não substituem os tetos individuais nem zeram consumo já registrado.

Valores padrão são **tetos locais conservadores**, não limites oficiais ou cota
disponível verificados na API: RPM 4, TPM 100.000 e RPD 20 por identificador de modelo.
`--reserve-demo 5` reserva cinco requisições do teto diário de **cada modelo**.
Assim, com RPD 20, esta bateria admite até 15 requisições por modelo por dia.
Agente e juiz que usam `gemini-3.1-flash-lite` compartilham o mesmo orçamento.

Para tetos distintos, copie e ajuste `config/evaluation_quotas.example.json` com
limites compatíveis com o projeto no AI Studio, sem inserir credenciais:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_pipeline --dry-run --quota-config config/evaluation_quotas.example.json --reserve-demo 5
```

Use `--quota-config` também no comando live quando a configuração tiver sido
verificada. O arquivo só aceita IDs já configurados no `.env`; ele não troca modelos.
Os campos são `rpm`, `tpm` e `rpd`, inteiros positivos. Flags `--rpm`, `--tpm` e
`--daily-limit` definem os defaults antes dos overrides específicos.

O orçamento persistente debita a tentativa **antes** do envio e salva consumo
observado após cada chamada. Falhas e interrupções mantêm a reserva conservadora.
RPD usa o reset diário do controle existente (meia-noite em America/Los_Angeles).
RPM/TPM usam janela móvel de 60 segundos. O intervalo global é pelo menos 15 s
na configuração atual, além do controle de chamadas já existente.
O lock de processo impede duas baterias desse novo executor em paralelo e é
liberado pelo sistema operacional após Ctrl+C ou encerramento do processo.

TPM antes do envio usa reserva conservadora baseada nos bytes do conteúdo/configuração,
margem de 1.024 tokens e teto de saída (`--max-output-tokens`, padrão 8.192).
Isso **não é contagem do tokenizer** nem consumo real: apenas admissão local.
Quando a API informa o total, a janela passa a usar esse valor; caso contrário,
mantém a reserva. Requisição estimada maior que o teto TPM para antes do envio.
Não há chamadas extras a `count_tokens`. Saída truncada pode invalidar o julgamento;
nessa situação a métrica permanece sem nota.

Qualquer HTTP 429 interrompe imediatamente a bateria — mais conservador que
aguardar falhas persistentes. Não se repete 429 automaticamente. `Retry-After`,
`RetryInfo` e evidência estruturada de limite diário são respeitados e persistidos.
O adaptador ainda permite seu retry único de 503 antes de qualquer texto;
cada tentativa é debitada e contabilizada. Outros erros operacionais também
interrompem a execução sem apagar o progresso anterior.

**Limitação:** o contador local começa a partir das chamadas deste executor e
não conhece uso prévio, outras máquinas ou chamadas do chat/scripts antigos.
Não consegue garantir uma reserva real no provedor se outros consumidores gastarem
a mesma cota. Consulte o AI Studio e reduza os tetos considerando esse uso.
Não remova arquivos de controle para contornar bloqueios. Não se promete concluir
os 13 casos no mesmo dia: o teto/reserva pode exigir mais de uma execução/dia.

## Progresso e relatórios

Cada execução cria `reports/evaluation/<data>-pipeline-<id>/` com:

- `plan.json`: fila e estimativa inicial;
- `progress.json`: fase/caso atual, etapas concluídas, parada e consumo conhecido;
- `calls.json`: ledger sanitizado por modelo, tokens retornados e status;
- `generate-Gxx/` e `judge-Gxx/`: relatórios JSON/Markdown individuais;
- `consolidated.json` e `consolidated.md`: todos os 18 casos, notas, origens e
  distinção entre concluídos, incompletos, parciais e falhas/não executados.

Orçamento e bloqueios ficam em `data/runtime/evaluation_pipeline/`, separados
por identificador derivado da chave (sem armazená-la). Gravações do orçamento,
ledger e progresso usam arquivo temporário e substituição atômica. Contextos e
respostas são salvos ao concluir geração; cada métrica válida é salva separadamente
antes do próximo caso. Se uma chamada estiver em voo durante uma interrupção,
não é possível recuperá-la sem que sua resposta tenha chegado; respostas parciais
não são consideradas concluídas e a reserva evita subcontabilizar a tentativa.

Scores, tokens e custos não são inventados. Tokens ausentes permanecem desconhecidos;
`known_total_tokens` agrega apenas metadados efetivamente recebidos, e
`requests_without_total_usage` identifica chamadas sem esse dado. Custos ficam nulos.
Relatórios antigos, inclusive notas zero válidas, e documentos RAG são preservados.

## Verificação sem chamadas reais

O dry-run do cache atual encontrou **13 pendentes**, estimando **49 chamadas**:
11 ao modelo principal, 27 ao modelo compartilhado de agentes/juiz e 11 de embeddings.
É planejamento, não consumo executado; não inclui retries ou reindexação eventual.
As gerações locais de ML/solicitação de entradas válidas não usam Gemini.
Com os tetos padrão, as 27 chamadas ao Lite excedem o orçamento diário local de 15;
o executor deve parar e retomar outro dia, salvo configuração verificada diferente.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Os testes usam SDK e chat simulados. Não foi iniciada a bateria real nesta alteração.

Resultado local: **196 testes aprovados em 42,39 s**, incluindo 12 testes do novo
executor e orçamento; `pip check` sem incompatibilidades. Conferência de 33 arquivos
históricos/cache: nenhum alterado. Chamadas reais ao Gemini: **zero**.
