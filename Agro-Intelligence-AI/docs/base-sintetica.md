# Cooperativa Agroindustrial Horizonte Sintético

Base integralmente fictícia para AI Factory / PUCPR. Não representa a C.Vale nem
qualquer outra cooperativa, pessoa, fabricante ou produto real. Não contém CPF,
CNPJ, contatos, endereços reais ou dados coletados de organizações.

## Auditoria anterior à alteração e preservação

A base anterior continha `clientes` (4 campos), `produtos` (5 campos) e `vendas`
(7 campos), carregados de `data/seeds/`. A consulta `commercial_snapshot` incluía
todas as vendas no prompt; os totais consideravam somente `status='faturada'`.
A interface tinha contagens fixas e o banco ficava em `data/runtime/comercial.duckdb`.

Os três CSVs originais foram copiados antes das alterações para
`data/backups/antes-expansao-*/`. O gerador também cria backup dos CSVs existentes
antes de cada publicação. Backups são locais e ignorados pelo Git. O banco antigo
permanece no caminho anterior; o app agora usa `data/runtime/cooperativa_v2.duckdb`.
Os três documentos em `data/documents/` e os módulos de RAG/Gemini foram preservados.

## Reprodução no Windows

```powershell
cd D:\Agro-Intelligence-AI
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Encerre o Streamlit com Ctrl+C antes de regenerar/carregar.
.\.venv\Scripts\python.exe -m scripts.generate_data
.\.venv\Scripts\python.exe -m scripts.init_data
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Semente padrão `20261015`, Faker `pt_BR` com `seed_instance`, numpy `default_rng` e
pandas. Versões fixadas no requirements. Período fixo: **01/10/2025 a 30/09/2026**.
Nada depende da data de execução; o timestamp é usado apenas no nome do backup.
Mesmo ambiente/versões e mesma semente produzem arquivos com os mesmos SHA-256.
`data/seeds/manifest.json` registra os hashes, contagens, semente e validações.
Para explorar outra realização sem mudar o app:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_data --seed 42 --output data/experimento
```

Os testes de regressão dos CSVs versionados e seus totais esperam a semente padrão.
Alterar a semente da base principal exige atualizar esses resultados de referência.

## Grão, relações e campos

| Tabela | Registros | Grão e campos principais |
|---|---:|---|
| regioes | 5 | código, nome fictício, UF e peso comercial |
| centros | 15 | três centros por região; FK região |
| clientes | 5.000 | código único, nome sintético, município sintético, UF e FK região |
| produtos | 1.000 | código, nome, família, unidade, preço/custo base, fabricante fictício |
| historico_precos | 12.000 | um produto por mês; FK produto, data, preço e custo |
| pedidos | 8.000 | código, cliente, centro, região, data, vencimento, status e valor líquido |
| vendas | 20.000 | **item de pedido**, FKs pedido/cliente/produto/centro/região, datas, quantidade, unidade, preços, custos, descontos, receita, margem, status e cenário |
| estoque | 3.000 | **produto × centro**, posição em 30/09/2026, unidade, físico, reservado, disponível, mínimo, máximo, custo e cenário |

Há 200 produtos de cada família: fertilizantes, agroquímicos, sementes de soja,
sementes de milho e nutrição foliar; 20 fabricantes explicitamente fictícios.
As unidades são `KG`, `L`, `tonelada`, `saca_40KG` e `saca_20KG`. Uma saca é sempre
contada como uma saca de seu tamanho específico; não se soma com KG ou outra saca.
Não há conversões automáticas entre produtos/unidades diferentes.

Cada produto é atendido pelos três centros de uma região (1.000 × 3 = 3.000 posições).
Toda linha comercial tem um par produto/centro no estoque. Clientes e centros de
um pedido pertencem à mesma região. Produtos não se restringem a uma família por
região. Os campos básicos antigos de clientes, produtos e vendas mantêm seus nomes,
e as funções `initialize_database` e `commercial_snapshot` mantêm seus contratos.
Consumidores externos que inseriam linhas pelo número antigo de colunas precisam
usar as novas colunas/relações; o aplicativo foi adaptado.

## Finanças e estados: evitar dupla contagem

Cada pedido tem um ou mais itens. Nesta versão não há faturamento parcial de um
pedido: todas as suas linhas herdam seu estado. `faturado` no pedido corresponde
a `faturada` nas linhas; `pendente` e `cancelado/cancelada` têm mapeamento equivalente.
Os 20.000 registros não representam 20.000 notas fiscais: são linhas comerciais.

- Faturamento realizado: receita líquida somente das linhas `faturada`.
- Carteira pendente: receita líquida somente das linhas `pendente`.
- Cancelado: valor separado, excluído de faturamento e carteira.
- `pedidos.valor_liquido` é a soma de seus itens em qualquer status. É uma visão
  alternativa da mesma operação; nunca somar novamente aos valores das linhas.
- Receita líquida = quantidade × preço unitário após desconto.
- Receita bruta = quantidade × preço de lista histórico.
- Desconto em valor = receita bruta − receita líquida.
- Custo total = quantidade × custo unitário.
- Margem em reais = receita líquida − custo total.
- Margem percentual = 100 × margem em reais / receita líquida (ponderada por receita
  nas agregações, nunca média simples dos percentuais).

Valores são calculados em centavos inteiros; o preço descontado usa half-up ao
centavo antes da multiplicação. A pequena diferença entre desconto nominal e
efetivo vem desse arredondamento. O DuckDB armazena dinheiro em `DECIMAL(18,2)`.
Não são simulados impostos, frete, devoluções ou despesas operacionais; essa margem
comercial bruta não é lucro líquido. Vencimentos são 30/60/90 dias depois da data
comercial e podem ultrapassar setembro de 2026. Não há baixa de títulos ou recebimentos.

Preços históricos são mensais, com tendência e pequena oscilação determinísticas;
o preço de lista da venda corresponde ao mês da operação. O catálogo de produtos
guarda o preço/custo base do início do período. Custos unitários excepcionais são
sobrescritos nos cenários de margem descritos abaixo, sem alterar o histórico base.

## Distribuições e cenários intencionais

Pesos comerciais por região: Oeste Simulado/PR 45%, Centro Simulado/PR 25%,
Vale Simulado/SC 15%, Sul Simulado/RS 10% e Cerrado Simulado/MS 5%. São probabilidades,
não quotas exatas nem estimativas de mercado. Os pesos de pedidos por mês, de
outubro a setembro, são **14,9,5,4,5,5,4,4,6,10,16,18** (soma 100); concentram
compras de insumos em julho–outubro. Datas, clientes, volumes e estados são sorteados.
Não há alegação de validação agronômica dessas distribuições.

| Cenário | Identificação exata | Comportamento |
|---|---|---|
| Ruptura | estoque.id 1–60 | físico e disponível zero |
| Excesso | estoque.id 61–120 | disponível 5.000 unidades do produto, máximo 1.000 |
| Desconto elevado e margem negativa | vendas.id 1–100 | desconto 18%, custo próximo de 92% da lista |
| Margem alta | vendas.id 101–200 | desconto zero, custo próximo de 60% da lista |
| Margem comprimida | vendas.id 201–300 | desconto 5%, custo igual ao preço efetivo, margem zero |

As demais 19.700 linhas e 2.880 posições têm cenário `normal`. Cenários comerciais
podem aparecer em qualquer estado; análises de faturamento devem continuar filtrando
`faturada`. Descontos de 18% são anomalias intencionais e não autorização para concedê-los.
A aprovação comercial não é simulada. Os documentos RAG originais têm escopo,
catálogo e vigência didáticos próprios; não são substituídos por estes dados.

Estoque é uma fotografia independente: não existe razão de movimentos, compras ou
estoque inicial para conciliá-lo cronologicamente às vendas. `reservado` é parte do
estoque físico, não toda a carteira futura. Não se deve presumir atendimento da
carteira a partir dessa coluna. Quantidades de estoque excessivo são deliberadas
para exercícios de análise, sem representar capacidade física real.

## Validação e segurança do contexto

O gerador valida antes de gravar. A carga valida novamente, cria um banco temporário
com PK/FK/UNIQUE/NOT NULL/CHECK e só o publica após sucesso. Hash dos CSVs e versão
do schema tornam a carga idempotente; dados inválidos preservam o banco anterior.
O app invalida o cache ao mudar tamanho/data dos CSVs. No Windows, feche o Streamlit
antes de substituir um banco em uso para evitar bloqueio do arquivo.

São verificadas nulidade, texto vazio, chaves duplicadas, FKs, unidades por produto,
pares de estoque, coerência entre pedido/item/região/centro, estados, preços positivos,
12 meses de histórico, preço da operação, datas e vencimentos, fórmulas financeiras,
totais de pedidos e disponibilidade de estoque. Os testes incluem dados corrompidos,
reprodução exata, backup e preservação de banco após rejeição de carga.

As consultas usam SQL fixo, agregam antes de limitar e retornam **até 20 linhas por
consulta**. O contexto do LLM exclui amostras de vendas e catálogo; leva totais,
12 meses, 5 regiões, 15 centros, famílias, vencimentos e evolução resumida de preços,
além de rankings de até 10 clientes e 10 alertas (5 rupturas e 5 excessos).
O chatbot seleciona somente as dimensões relacionadas às perguntas recentes; a
visão ampla pode ser solicitada como “resumo geral”. Essa seleção usa palavras-chave,
não um modelo de ML, e pode exigir reformular perguntas com a dimensão desejada.
O teste de contexto limita o texto estruturado + instruções a 24.000 caracteres
com uma fonte simulada. Isso não é um limite de tokens da API; os trechos RAG e
até 20 mensagens do histórico acrescentam conteúdo. Nenhum registro bruto em massa
é incluído no prompt. O app mostra três indicadores e amostras limitadas em expansor.

## Perguntas que os indicadores permitem responder

- Qual é o faturamento realizado e o valor da carteira pendente?
- Quais são as dez maiores receitas faturadas por cliente?
- Como o faturamento evoluiu por mês? Qual mês teve maior receita?
- Qual região e qual centro têm maior faturamento?
- Quais famílias têm menor margem comercial percentual?
- Quantas posições estão em ruptura e em excesso? Mostre alguns exemplos.
- Qual o volume faturado por unidade, sem somar KG, litros e sacas?
- Como a carteira pendente se distribui por mês de vencimento?
- Quanto as linhas de desconto elevado faturaram e qual sua margem?
- Como os preços médios por família/unidade mudaram entre início e fim do período?

O contexto não contém todos os clientes/produtos. Detalhes de um cliente arbitrário
fora do ranking ou todas as posições de estoque não devem ser inventados. As regras
de pagamento/desconto continuam consultáveis via RAG, com as limitações de vigência
e escopo dos documentos originais.

## Resultado executado nesta ampliação

- **62 testes automatizados aprovados** no Windows/Python 3.11.9, incluindo a interface
  Streamlit, histórico/streaming simulados e busca/persistência ChromaDB.
- **93 verificações de dados aprovadas** sobre os CSVs finais; hashes SHA-256 conferidos
  e contagens/totais reconciliados com o novo DuckDB.
- `pip check`: nenhuma dependência incompatível.
- As cinco consultas de `queries/examples.sql` foram executadas com sucesso e
  respeitaram o limite de 20 resultados.
- Contexto completo com três documentos didáticos medido em **16.660 caracteres**,
  sem lista de vendas ou catálogo bruto e sem chamada remota.
- Pedidos: **5.772 faturados, 1.832 pendentes e 396 cancelados**.
- Faturamento: **R$ 493.126.517,02**; carteira: **R$ 155.146.363,54**;
  cancelado: **R$ 34.784.595,17**; margem sobre faturadas: **R$ 100.023.056,21**.
- Banco legado confirmado no caminho antigo. Nenhum documento RAG foi substituído
  e nenhuma chave/arquivo `.env` foi modificado nesta ampliação.

Esses resultados validam a implementação local e a consistência dos dados. Não foi
feita nova chamada real ao Gemini nesta etapa; disponibilidade/cota remota continua
dependendo da conta e do provedor.

**Esta base é para desenvolvimento e testes funcionais. Não comprova desempenho,
generalização ou validade de um modelo de Machine Learning. Treinamento, avaliação
com conjuntos independentes e eventual validação com dados reais são trabalhos separados.**
