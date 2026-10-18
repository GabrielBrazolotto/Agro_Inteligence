# Auditoria — rupturas e margem regional — 17/10/2026

## Base conferida diretamente

Banco `data/runtime/cooperativa_v2.duckdb`, somente leitura, sem alterar dados,
documentos RAG, modelo ML ou segredos. A suíte anterior passou com 91 testes.
Estoque: 3.000 registros e 3.000 pares produto/centro distintos, posição de
30/09/2026. Período comercial: 01/10/2025 a 30/09/2026. Dados inteiramente sintéticos.

## O que significam 60 rupturas e R$ 74.151.160,39

A consulta anterior retornava dois indicadores de escopos diferentes. Não havia
erro na soma do grupo amplo; a interpretação podia atribuí-la só às rupturas.

| Categoria mutuamente exclusiva | Posições | Carteira de itens pendentes |
|---|---:|---:|
| Disponível = 0 (ruptura observada) | 60 | R$ 4.399.084,73 |
| Disponível > 0 e carteira em quantidade > disponível | 695 | R$ 69.752.075,66 |
| União das duas categorias (sinalizados) | 755 | R$ 74.151.160,39 |

Das 60 posições zeradas, **41 têm carteira pendente**. O valor de R$ 4.399.084,73
corresponde a **103 itens de 101 pedidos distintos**. Não é o valor integral desses
101 pedidos, pois outros itens deles podem não pertencer a posições zeradas.

Custos desses itens pendentes: **R$ 3.506.069,23**. Margem comercial de sua carteira:
**R$ 893.015,50**. Esses valores não são faturamento, margem realizada, perda
confirmada ou previsão estatística de perda.

Foi reconciliada a soma agregada por par com uma consulta independente de itens
pendentes usando `EXISTS` para posições com disponível zero. Os valores coincidem.
Não há duplicação de pares de estoque, o CTE pendente agrega antes do join e
`EXISTS` não multiplica os itens. O total dos pedidos não é somado aos seus itens.
Contagem de pedidos é `COUNT(DISTINCT pedido_id)`; contagens por família não devem
ser somadas para inferir pedidos distintos globais.

O agente agora prioriza posições zeradas quando a pergunta menciona ruptura.
Mantém os indicadores amplos com nomes explícitos para compatibilidade. O comercial
consulta os até 20 pares compartilhados e também uma consulta independente para
**todas** as rupturas, evitando apresentar a amostra como valor global.

Isso continua sendo comparação descritiva da fotografia de estoque com a carteira.
Não existe razão de movimentos para provar que um pedido histórico deixou de ser
atendido por essa fotografia. Não é forecast de abastecimento nem alerta certificado.

## Margem regional: os dados existem

`vendas` contém `regiao_id`, `status`, `receita_liquida`, `custo_total` e
`margem_valor`. Nos **14.431 itens faturados**, não há nulos nesses campos nem
divergências em `margem_valor = receita_liquida - custo_total`.

Receita faturada total: **R$ 493.126.517,02**; custo dos itens faturados:
**R$ 393.103.460,81**; margem comercial bruta: **R$ 100.023.056,21**.

A consulta regional anterior disponibilizava somente receita, por isso o agente
não tinha evidência no contexto para responder a margem regional. A consulta foi
ampliada, preservando seus campos anteriores, com custo, margem em reais e percentual:

```sql
SELECT r.codigo, r.nome AS regiao,
       SUM(v.receita_liquida) AS receita_faturada,
       SUM(v.custo_total) AS custo_faturado,
       SUM(v.receita_liquida - v.custo_total) AS margem_faturada,
       ROUND(100 * SUM(v.receita_liquida - v.custo_total)
             / NULLIF(SUM(v.receita_liquida), 0), 4) AS margem_pct
FROM vendas v
JOIN regioes r ON r.id = v.regiao_id
WHERE v.status = 'faturada'
GROUP BY r.codigo, r.nome
ORDER BY receita_faturada DESC
LIMIT 20;
```

| Região | Receita faturada | Margem em reais | Margem consolidada |
|---|---:|---:|---:|
| Oeste Simulado | R$ 225.379.335,16 | R$ 45.563.410,93 | 20,2163% |
| Centro Simulado | R$ 125.389.865,57 | R$ 25.923.226,73 | 20,6741% |
| Vale Simulado | R$ 74.180.338,74 | R$ 15.003.287,63 | 20,2254% |
| Sul Simulado | R$ 43.933.226,58 | R$ 8.621.540,89 | 19,6242% |
| Cerrado Simulado | R$ 24.243.750,97 | R$ 4.911.590,03 | 20,2592% |

Essa é margem ponderada pela receita, **não a média simples dos percentuais dos
itens**. A soma regional de receitas, custos e margens reconcilia com o total das
faturadas; pendentes e canceladas não entram. `NULLIF` evita divisão por zero; uma
região sem receita não deve receber percentual inventado.

Política contábil do protótipo: receita líquida já deduz descontos, logo não os
subtrair novamente. `custo_total` já é quantidade × custo unitário da operação;
não usar o custo atual do catálogo nem multiplicar novamente pela quantidade.
Impostos, frete, devoluções e despesas operacionais não são simulados. Portanto,
não se pode afirmar lucro líquido regional ou margem contábil completa sem esses
campos/regras adicionais. Não foi adotada uma nova política contábil.

## Coordenação, ML e reprodução

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_commercial
# Opcional: executa as duas perguntas também com Gemini/RAG, consumindo cota.
.\.venv\Scripts\python.exe -m scripts.audit_commercial --live
.\.venv\Scripts\python.exe -m pytest -q
```

Relatórios: `reports/audit/commercial_local.json` e, quando executado com `--live`,
`reports/audit/commercial_live.json`. Incluem consultas reconciliadas, resultados
intermediários, agentes, dependências, fontes, análises e resposta. O modo local
declara que não chamou LLM e registra RAG indisponível, sem fingir sucesso remoto.

Na tarefa composta, a sequência é Estoque → `duckdb_estoque_pedidos` → pares com
saldo zero → Comercial → `duckdb_comercial`, `duckdb_impacto_pares`,
`duckdb_impacto_rupturas_total`, `chroma_rag_comercial` → síntese. A consulta global
de rupturas usa o mesmo escopo comunicado pelo estoque; a amostra permanece separada.

Nenhuma das duas perguntas solicita inferência ML: o registro não deve conter
`scikit_learn_backorder`. Para pedidos de previsão, a ferramenta valida as sete
entradas e chama o pipeline somente quando válidas. Casos sem entradas ou com
seis entradas ficam `needs_input`; com sete valores compatíveis há inferência
real. Os testes rejeitam também campos extras/duplicados e valores inválidos.

Os agentes continuam sujeitos a formulações incorretas do LLM. Valores intermediários
auditados e escopos devem ser conferidos; não há garantia de veracidade de toda
síntese livre, nem de disponibilidade futura do serviço Gemini.

## Resultado da execução

- **94 testes aprovados** após a alteração; `pip check` sem incompatibilidades.
- As duas perguntas foram executadas com **Gemini/RAG reais**, com todas as chamadas
  registradas em estado `ok` em `reports/audit/commercial_live.json`.
- Na primeira, os agentes Estoque e Comercial participaram, incluindo compartilhamento
  de 20 pares com saldo zero, consulta global de rupturas, RAG, análises e síntese.
  A resposta apresentou R$ 4.399.084,73 de carteira e R$ 893.015,50 de margem da carteira.
- Na segunda, o agente Comercial recebeu custos e margens regionais e a resposta
  apresentou as cinco regiões e percentuais coerentes com o DuckDB.
- Nenhuma das perguntas acionou o modelo ML. A verificação independente retornou
  `needs_input` com zero/seis entradas e inferência real com sete entradas válidas.
- O modo local foi executado separadamente; suas lacunas de RAG estão explícitas.

Arquivos alterados/criados: `agro_ai/database.py`, `agro_ai/assistant.py`,
`agro_ai/agents/tools.py`, `agro_ai/agents/orchestrator.py`,
`scripts/audit_commercial.py`, `tests/test_financial_audit.py`, `README.md`,
este documento e os relatórios locais/de execução real. Nenhum dado comercial,
documento RAG ou artefato do modelo foi substituído.
