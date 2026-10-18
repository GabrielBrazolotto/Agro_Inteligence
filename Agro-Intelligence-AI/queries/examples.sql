-- Abrir data/runtime/cooperativa_v2.duckdb. Dados exclusivamente sintéticos.
-- Não somar total de pedidos e itens: representam as mesmas operações.

-- Faturamento, carteira e cancelamentos separados.
SELECT status, COUNT(*) AS itens, COUNT(DISTINCT pedido_id) AS pedidos,
       SUM(receita_liquida) AS valor
FROM vendas GROUP BY status ORDER BY status LIMIT 20;

-- Margem ponderada por família (somente faturadas).
SELECT p.categoria, SUM(v.receita_liquida) AS receita,
       SUM(v.margem_valor) AS margem,
       ROUND(100 * SUM(v.margem_valor) / SUM(v.receita_liquida), 4) AS margem_pct
FROM vendas v JOIN produtos p ON p.id=v.produto_id
WHERE v.status='faturada' GROUP BY p.categoria ORDER BY margem_pct LIMIT 20;

-- Faturamento por mês e região: 20 maiores combinações, não o total geral.
SELECT strftime(v.data_venda,'%Y-%m') AS mes, r.nome AS regiao,
       SUM(v.receita_liquida) AS receita
FROM vendas v JOIN regioes r ON r.id=v.regiao_id WHERE v.status='faturada'
GROUP BY mes,r.nome ORDER BY receita DESC,mes,r.nome LIMIT 20;

-- Exemplos de estoque excessivo com unidade explícita.
SELECT p.codigo AS produto,c.codigo AS centro,e.unidade,e.disponivel,e.estoque_maximo
FROM estoque e JOIN produtos p ON p.id=e.produto_id JOIN centros c ON c.id=e.centro_id
WHERE e.disponivel>e.estoque_maximo ORDER BY e.id LIMIT 20;

-- Valor/margem das anomalias, sem misturar estados.
SELECT cenario,status,COUNT(*) AS itens,SUM(receita_liquida) AS receita,SUM(margem_valor) AS margem
FROM vendas WHERE cenario<>'normal' GROUP BY cenario,status ORDER BY cenario,status LIMIT 20;
