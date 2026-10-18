"""Oráculo SQL independente, fixo, agregado, limitado e somente leitura."""
from decimal import Decimal
import re
import unicodedata
import duckdb

QUERIES={
 'revenue':"SELECT SUM(receita_liquida) valor FROM vendas WHERE status='faturada'",
 'margin':"SELECT SUM(receita_liquida-custo_total) valor FROM vendas WHERE status='faturada'",
 'pending':"SELECT SUM(receita_liquida) valor FROM vendas WHERE status='pendente'",
 'ruptures':'SELECT COUNT(*) valor FROM estoque WHERE disponivel=0',
 'excess':'SELECT COUNT(*) valor FROM estoque WHERE disponivel>estoque_maximo',
 'monthly':"SELECT strftime(data_venda,'%Y-%m') mes,SUM(receita_liquida) valor FROM vendas WHERE status='faturada' GROUP BY mes ORDER BY mes LIMIT 12",
 'regional':"SELECT r.nome regiao,SUM(v.receita_liquida) valor,ROUND(100*SUM(v.receita_liquida-v.custo_total)/NULLIF(SUM(v.receita_liquida),0),4) margem_pct FROM vendas v JOIN regioes r ON r.id=v.regiao_id WHERE v.status='faturada' GROUP BY r.nome ORDER BY valor DESC LIMIT 20",
 'rupture_pending':"SELECT SUM(v.receita_liquida) valor FROM vendas v WHERE v.status='pendente' AND EXISTS (SELECT 1 FROM estoque e WHERE e.produto_id=v.produto_id AND e.centro_id=v.centro_id AND e.disponivel=0)",
}


def reference_rows(database,name):
    with duckdb.connect(str(database),read_only=True) as connection:
        cursor=connection.execute(QUERIES[name])
        return [dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]


def answer_numbers(answer):
    # Reconhece formatação BR e ponto decimal; não aceita valores arredondados em milhões.
    numbers=set()
    for raw in re.findall(r'(?<![\w])[-+]?\d[\d.,]*(?![\w])',answer):
        raw=raw.rstrip('.,')
        try:
            numbers.add(Decimal(raw.replace('.','').replace(',','.')) if ',' in raw else Decimal(raw))
        except Exception:
            pass
    return numbers


def check_finances(database,checks,answer):
    values=answer_numbers(answer)
    results=[]
    for name in checks:
        rows=reference_rows(database,name)
        missing=[]
        for row in rows:
            group=row.get('mes',row.get('regiao'))
            candidates=values
            if group:
                def normalized(text):
                    text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
                    return re.sub(r'[^a-z0-9]+',' ',text).strip()
                matching=[line for line in answer.splitlines() if normalized(str(group)) in normalized(line)]
                candidates=answer_numbers('\n'.join(matching))
            for key in ('valor','margem_pct'):
                if key in row:
                    target=Decimal(str(row[key]))
                    tolerance=Decimal('.005') if key=='valor' else Decimal('.005')
                    if not any(abs(value-target)<=tolerance for value in candidates):
                        missing.append({'field':key,'expected':str(target),'group':row.get('mes',row.get('regiao'))})
        results.append({'check':name,'status':'failed' if missing else 'passed','reference_rows':rows,
                        'missing_or_inaccurate_values':missing})
    return results
