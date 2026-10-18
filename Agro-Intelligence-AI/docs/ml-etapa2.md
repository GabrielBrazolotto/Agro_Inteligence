# Etapa 2 — classificação experimental de risco de backorder

## Decisão de dataset antes da implementação

A arquitetura foi inspecionada e os **65 testes existentes passaram** antes das
alterações. O aplicativo tem interface Streamlit, consultas fixas DuckDB, RAG
ChromaDB e embeddings/streaming Gemini. O DuckDB ampliado foi aberto em modo
somente leitura. `estoque` contém 3.000 posições em **uma única data, 30/09/2026**;
os cenários de ruptura e excesso foram definidos pelo gerador sintético.

Usar `disponivel == 0` ou `cenario == ruptura` como alvo e treinar com as mesmas
quantidades seria reproduzir uma regra e vazamento de alvo. Não há evento futuro
observado, sequência de posições, recebimentos ou rótulos de atendimento nessa
base. Portanto, ela **não é dataset de treino/avaliação deste modelo**.

A alternativa foi apresentada antes de implementar: **Can You Predict Product
Backorders?**, com alvo original `went_on_backorder`, classe positiva `Yes`.
Backorder significa demanda/pedido não atendido pela disponibilidade imediata,
um problema relacionado a reposição de fertilizantes, sementes e outros insumos.
Não é sinônimo perfeito de ruptura física nem prova de risco futuro em horizonte
definido no domínio brasileiro.

Fontes documentais:

- [Descrição dos campos na competição Kaggle](https://www.kaggle.com/c/untadta/data).
- [Espelho público e dicionário de dados](https://github.com/akhiilkasare/Back-Order-Prediction-iNeuron/tree/3bf0817ebb1a20e675ff02244660507e59f180f2).
- [Artigo de pesquisa sobre esse problema/dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC8659943/).

Não foram copiados modelos, scripts ou métricas desses trabalhos. Somente o ZIP de
dados foi baixado; o código de treino/inferência deste projeto foi implementado aqui.
O SHA-256 verificado do arquivo é
`70ed395f05bcac971cd610dfb5c31832548e5fc0804b8aa58b131c99c9dc7c5f`.
A URL fixa um commit, não acompanha a branch automaticamente. O arquivo CSV é
`Training_Dataset_v2.csv`, com **1.687.861 linhas lidas: 1.687.860 rotuladas e um
rodapé sem alvo**. Das rotuladas, 11.293 são `Yes` e 1.676.567 são `No`.

O mirror identifica licença GPL-3.0 para o repositório; isso não comprova uma licença
independente dos dados originais da competição. Os dados brutos ficam localmente
em `data/ml/raw/`, ignorados pelo Git. Confirmar os termos de origem antes de
redistribuição ou uso comercial. Procedência do ERP/empresa e processo de coleta
não foram auditados independentemente.

## Atributos e significado

O contrato único fica em `agro_ai/ml/schema.py`. Treino e inferência usam **exatamente
estas sete colunas**, nesta ordem:

| Atributo da fonte | Nome aceito no chat | Significado |
|---|---|---|
| national_inv | estoque | nível de estoque do produto na fonte |
| lead_time | prazo | tempo de trânsito/reposição |
| in_transit_qty | transito | quantidade em trânsito |
| forecast_3_month | previsao_3m | previsão de demanda para três meses disponível na origem |
| sales_1_month | vendas_1m | vendas do mês anterior |
| sales_3_month | vendas_3m | vendas dos três meses anteriores |
| min_bank | estoque_minimo | mínimo recomendado na origem |

As quantidades devem estar na **mesma unidade por produto**. A fonte consultada
descreve lead time como tempo de trânsito, mas não estabelece inequivocamente sua
unidade; não supor dias nem converter unidades para aplicação operacional sem
confirmação. Forecasts são entradas fornecidas pela origem/usuário, não previsões
criadas pelo chatbot. O horizonte do rótulo não é estabelecido por datas no CSV.

Excluídos: SKU/identificadores, alvo, quantidade de backorder já existente, partes
vencidas e flags de risco. Elas podem revelar estado contemporâneo, regras prévias
ou informação cuja disponibilidade no momento da decisão não foi comprovada.
Também foram excluídos atributos adicionais para manter o contrato simples.
Isso reduz fontes óbvias de vazamento, mas não audita a causalidade/temporalidade
do dataset original. Estoque atual pode codificar informação contemporânea ao evento.

O DuckDB não contém todos os sete atributos equivalentes. Portanto, o chat não
converte automaticamente `PRD-...` em uma previsão, não usa os cenários sintéticos
como alvo e não supõe estoque em trânsito zero ou uma previsão de demanda fictícia.
Solicita os valores que faltam. Nenhum dado de C.Vale foi usado.

## Treino e avaliação

1. Verificar checksum, ler apenas as colunas necessárias, excluir rodapé sem alvo,
   verificar unicidade de SKU e converter `Yes/No` para `1/0`, sem gerar rótulos.
2. Amostrar uniformemente até **200.000 linhas**, semente `20261015`, sem balancear
   pela classe. `--max-rows 0` permite treinar sobre todas as linhas válidas.
3. Agrupar pelo vetor dos sete atributos, antes de separar dados. Entradas idênticas,
   mesmo com alvos conflitantes, ficam na mesma partição. SKU é único na origem.
4. Separar teste com StratifiedGroupKFold de 5 partes; dividir desenvolvimento
   novamente em treino/validação. Aproximadamente 64/16/20%; tamanhos reais dependem
   dos grupos e estão em `reports/ml/metrics.json`. Atribuições ficam em CSV auditável.
5. Treinar Pipeline com **HistGradientBoostingClassifier**, 160 iterações,
   15 folhas, learning rate 0,07, regularização L2 1, pesos de classe balanceados
   calculados somente no treino. HGB aprende o tratamento de ausentes no treino;
   valores sentinela -99 de lead time são convertidos em ausentes sem usar estatísticas.
6. Escolher limiar em grade fixa 0,05–0,95 pelo maior **F2 na validação**. Não escolher
   modelo, atributos, pesos ou limiar com o teste. Não há oversampling/SMOTE.
7. Avaliar uma vez no teste reservado e comparar com DummyClassifier que sempre
   prevê a classe majoritária. Salvar accuracy, precision, recall, F1, ROC-AUC,
   average precision e matriz de confusão. A classe positiva é backorder.

**Não há divisão temporal**: não existem datas para aplicá-la de maneira legítima.
Uma divisão aleatória agrupada não prova previsão de eventos futuros. Nem teste
nem validação entram no ajuste do modelo; não há refit sobre essas partições.
Os scores ponderados **não são probabilidades calibradas** e não devem ser lidos
como “chance real de ruptura de X%”. O limiar selecionado é experimental, não uma
política ótima de custos da cooperativa.

## Resultado real executado

Artefato treinado: `models/backorder/model.joblib`, Pipeline scikit-learn. Amostra
uniforme de **200.000 registros**, com 1.367 positivos (0,6835%). Partições realizadas:

| Partição | Registros | Backorders |
|---|---:|---:|
| Treino | 128.000 | 875 |
| Validação | 32.000 | 219 |
| Teste reservado | 40.000 | 273 |

Nenhum grupo de atributos idênticos cruza essas partições. Limiar escolhido na
validação por F2: **0,91**. Hiperparâmetros e atributos não foram alterados em função
das métricas do teste. Uma repetição técnica com a mesma configuração produziu
as mesmas métricas; ela não é uma avaliação independente adicional.

| Métrica no teste | Modelo treinado | Baseline sempre “No” |
|---|---:|---:|
| Accuracy | 98,1400% | 99,3175% |
| Precision positiva | 16,6902% | 0% |
| Recall positivo | 43,2234% | 0% |
| F1 positivo | 24,0816% | 0% |
| ROC-AUC | 0,935928 | 0,500000 |
| Average precision | 0,164731 | 0,006825 |

Matriz de confusão real:

| Real / Previsto | Sem backorder | Backorder |
|---|---:|---:|
| Sem backorder | 39.138 | 589 |
| Backorder | 155 | 118 |

O modelo deixou de detectar **155 de 273 eventos** e gerou 589 falsos alertas.
Portanto, estes números não justificam alertas automáticos de produção. A accuracy
do baseline é maior justamente porque ignora a classe rara. Não se deve promover
accuracy de 98,14% como evidência isolada de bom desempenho comercial.

A pergunta de exemplo com estoque=10, prazo=8, trânsito=0, previsão_3m=100,
vendas_1m=20, vendas_3m=60 e estoque_minimo=15 foi executada pela rota local:
**classe 1, score 0,9266898444, limiar 0,91**. A resposta é “risco sinalizado de
backorder”, não “92,67% de chance real”. O exemplo do arquivo `example.json` é
outro caso público, também verificado contra o pipeline persistido.

Validação local: **80 testes passaram** na suíte completa após o treino; os 65
testes iniciais passaram antes da implementação. Os novos testes verificam o contrato
dos sete atributos, entradas inválidas, grupo sem vazamento, checksum, descarte
de rodapé, métricas recomputadas, inferência do artefato e chat sem Gemini.
`pip check` não encontrou dependências incompatíveis. Nenhuma chamada real à API
Gemini foi necessária nesta etapa; o funcionamento remoto atual não foi revalidado.

## Prioridade comercial das métricas

**Recall da classe positiva** merece prioridade quando deixar de identificar falta
de insumo provoca perda de venda ou atraso em uma janela de plantio. Contudo,
falsos positivos podem aumentar compras e estoque: acompanhar precision e a
quantidade de alertas. F2 dá mais peso ao recall nesse protótipo. Accuracy isolada
é inadequada à classe rara; um modelo que nunca alerta pode ter accuracy alta.
ROC-AUC mede ranking; average precision ajuda a enxergar a classe rara.
Custos reais, capacidade de atendimento e calibração são necessários antes de
fixar limiar de produção. Nenhum benefício financeiro foi estimado ou inventado.

## Executar no Windows

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.train_ml --download
.\.venv\Scripts\python.exe -m scripts.predict_ml --example
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

O treino é local/CPU e não usa Gemini. A primeira execução precisa de rede apenas
para o download. O artefato fica em `models/backorder/model.joblib`, junto de
`metadata.json` com hash, versões, colunas, limiar, partições e métricas. Não carregar
arquivos joblib/pickle recebidos de terceiros. O hash detecta corrupção, não é
assinatura de autenticidade. O modelo só é carregado na rota ML.

Matriz de confusão: `reports/ml/confusion_matrix.png`; linhas = classe verdadeira,
colunas = previsão; ordem `[sem backorder, backorder]`. As previsões de teste em
`test_predictions.csv` permitem recalcular as métricas. Não altere o limiar após
examinar o teste para alegar uma nova avaliação independente.

## Previsão no chat

```text
Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15
```

O parser determinístico apenas extrai/valida valores explícitos; **não classifica
por regras**. A classe e o score vêm de `pipeline.predict_proba`. Campos faltantes,
repetidos, desconhecidos, não finitos ou inválidos são rejeitados. Não se somam
KG/sacas/litros. A resposta mostra todos os valores efetivamente usados, o limiar
e as limitações. Valores fora da faixa do treino recebem aviso de extrapolação.

A previsão local funciona sem chamadas ao Gemini e, com o artefato, sem chave da
API. Perguntas comerciais ou de RAG preservam o fluxo anterior. Histórico e limpeza
da conversa são compartilhados. Sem artefato, o sistema pede o treinamento e não
inventa uma previsão. `scripts.predict_ml --input atributos.json` aceita o mesmo
contrato de sete campos, usando os nomes originais.

## Limitações e escopo

Não é modelo de produção para a cooperativa. Há desbalanceamento, limitação de
procedência e de horizonte, ausência de teste temporal e possível informação
contemporânea nos campos da fonte. A amostra e o domínio público externo podem
ter distribuições diferentes das operações agrícolas. Não há calibração, teste
prospectivo, monitoramento de drift nem validação de custos.

As métricas descrevem somente o teste reservado desse dataset público. **Não são
resultados de uma cooperativa, nem avaliação nos dados sintéticos ampliados.**
Para uso real, coletar snapshots pré-evento, atributos disponíveis na data da
decisão, movimentos/recebimentos e alvos futuros por produto/centro; separar por
tempo e entidade e validar prospectivamente. CrewAI, Langfuse e DeepEval continuam
fora do escopo.
