# Material de entrega — Etapa 2, AI Factory / PUCPR

## Arquivos

- `relatorio-academico.md`: texto em primeira pessoa, 1.081 palavras pelo critério documentado em `validacao-entrega.json`.
- `resumo-tecnico-avaliacoes.md`: tabela dos 15 casos com pergunta original, categoria, notas, oráculo DuckDB e observações; fontes por métrica.
- `avaliacoes-g01-g15.csv`: mesma tabela para abrir no Excel, com notas sem arredondamento de exibição.
- `evidencias-avaliacoes.json`: respostas, evidências recuperadas, ferramentas, vereditos e hashes de origem. Inclui somente dados fictícios do projeto e resultados públicos/experimentais de ML.
- `evidencias-ml.json`: cópia dos metadados reais do modelo, com dataset, variáveis, partições, métricas e limites.
- `verificacao-ml.json`: recálculo local das métricas a partir das 40.000 predições de teste salvas, sem inferência ou treino novos.
- `verificacao-seguranca.json`: varredura sanitizada de arquivos de texto e exclusões recomendadas.
- `validacao-entrega.json`: confirmação de 15 casos/30 métricas `evaluated`, médias, contagem de palavras e imagens pendentes.
- `imagens/matriz-confusao-backorder.png`: cópia da matriz de confusão real já existente.

Os metadados originais estão em `models/backorder/metadata.json`, e a fonte é
[Can You Predict Product Backorders? — espelho público em commit fixo](https://github.com/akhiilkasare/Back-Order-Prediction-iNeuron/tree/3bf0817ebb1a20e675ff02244660507e59f180f2).
Não foram consultadas páginas externas ou APIs nesta preparação. Procedência e
limitações são as documentadas no projeto e nos metadados locais. Não redistribuir
o ZIP bruto do dataset sem conferir os termos da origem.

## Duas capturas ainda precisam ser inseridas

1. **Lista de pelo menos cinco traces no Langfuse**, no primeiro marcador do relatório.
   Salvar como `imagens/langfuse-cinco-traces.png`. Mostrar nomes e estados reais;
   a existência de falhas/fallback deve ficar visível quando fizer parte do registro.
2. **Uma execução detalhada**, no segundo marcador do relatório.
   Salvar como `imagens/langfuse-execucao-detalhada.png`. Mostrar a árvore da raiz
   `agro.chat.request`, orquestração, agentes, ferramentas, geração, latências e status.

Use traces já existentes, sem gerar chamadas novas só para a captura. O arquivo
`reports/observability/validation.json` registra cinco traces completos confirmados
via API, com `ui_visually_confirmed=false`. Isso não é comprovação visual nem
confirmação de disponibilidade atual do servidor; as capturas continuam pendentes.

IDs documentados que ajudam a encontrar as execuções:

| Registro | Trace ID | Situação registrada |
|---|---|---|
| 1 | c5041274d2604310b2b437adc0038c7d | ok |
| 2 | d266da08849f0b3d9444b89bb9d816e2 | ok |
| 3 | 35033a7f2aec215060ef4e398f72609f | fallback |
| 4 | 56808ce669396cc15a463959bed3cd3a | fallback; dois agentes |
| 5 | 05d850d53c649d6b63c95cf8349e33fd | fallback; dois agentes e ML |

Para a segunda captura, o registro 5 documenta `agro.agent.estoque`,
`agro.agent.comercial`, spans DuckDB/Chroma, `agro.ml.predict_backorder` e geração.
Não descrever essa execução como integralmente bem-sucedida: o registro contém fallback.

Depois de inserir as capturas, substitua os dois marcadores por imagens Markdown
ou pelas figuras no editor usado para exportar o relatório. Remova credenciais,
emails, identificadores de conta e conteúdo privado da tela. Não capture a aba `.env`.
As imagens ainda não foram examinadas e não estão incluídas nesta entrega local.

## Segurança e preparação para repositório ou ZIP

A varredura atual não encontrou valores das credenciais configuradas nem padrões
de chaves nos arquivos de texto selecionados. `.env.example` está sem valores de
credenciais; `.env` existe e precisa permanecer fora da entrega.
A `.gitignore` exclui ambiente, runtime e dados brutos. Um ZIP manual **não respeita
automaticamente a `.gitignore`**: selecione os arquivos explicitamente.

Não inclua `.env`, outros arquivos de segredo, `.venv`, runtime Chroma/DuckDB,
logs, backups ou dataset bruto. Evite publicar `reports/ml/split_assignments.csv`;
as métricas agregadas são suficientes para a entrega acadêmica. O artefato local
do modelo tem hash conferido, mas a distribuição de dados/modelos deve observar
os termos da fonte pública e as exigências da disciplina.

Não existe diretório `.git` neste workspace; portanto não foi possível auditar
histórico de commits ou garantir ausência de segredos em um repositório remoto.
A análise foi local e textual, não inclui OCR de screenshots, arquivos binários
nem prova de ausência de todo tipo de segredo. **Nenhum ZIP foi criado** nesta etapa.

## Reprodução offline

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_etapa2_delivery
```

Esse comando lê o cache e fontes, confere as notas originais, reexecuta somente
o oráculo SQL local e atualiza os arquivos complementares desta pasta. Não chama
Gemini/Langfuse, não gera respostas, não retreina o modelo e não modifica relatórios
históricos. O relatório acadêmico é mantido como texto revisado manualmente.

As médias abrangem protocolos históricos diferentes. A avaliação dos 15 casos
concluídos não substitui revisão humana nem mede generalização de ML.
