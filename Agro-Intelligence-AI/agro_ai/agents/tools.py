"""Ferramentas permitidas: consultas fixas, leitura, parâmetros e limites explícitos."""
import duckdb

from agro_ai.database import commercial_snapshot
from agro_ai.assistant import select_commercial_context
from agro_ai.ml.inference import parse_features, predict_risk, MLInputError
from agro_ai.observability import observe

PENDING = """WITH pendentes AS (
 SELECT produto_id,centro_id,SUM(quantidade) AS quantidade,SUM(receita_liquida) AS valor
 FROM vendas WHERE status='pendente' GROUP BY produto_id,centro_id),
 situacao AS (SELECT e.*,COALESCE(p.quantidade,0) AS carteira_quantidade,
 COALESCE(p.valor,0) AS carteira_valor,
 (e.disponivel=0 OR COALESCE(p.quantidade,0)>e.disponivel) AS sinalizado
 FROM estoque e LEFT JOIN pendentes p USING(produto_id,centro_id)) """


class SystemTools:
    def __init__(self, database, index=None):
        self.database = database
        self.index = index

    @observe('duckdb.stock_and_orders')
    def stock_and_orders(self, scope='sinalizados'):
        if scope not in ('ruptura','sinalizados'):
            raise ValueError('Escopo inválido.')
        condition='s.disponivel=0' if scope=='ruptura' else 's.sinalizado'
        with duckdb.connect(str(self.database), read_only=True) as con:
            cur = con.execute(PENDING + """SELECT MAX(data_referencia) AS data_estoque,
              COUNT(*) AS posicoes, COUNT(*) FILTER(WHERE disponivel=0) AS rupturas_observadas,
              COUNT(*) FILTER(WHERE disponivel>estoque_maximo) AS excessos,
              COUNT(*) FILTER(WHERE sinalizado) AS pares_sinalizados,
              COUNT(*) FILTER(WHERE disponivel=0 AND carteira_quantidade>0) AS rupturas_com_carteira,
              SUM(CASE WHEN disponivel=0 THEN carteira_valor ELSE 0 END) AS carteira_em_ruptura,
              COUNT(*) FILTER(WHERE disponivel>0 AND carteira_quantidade>disponivel) AS insuficiencias_com_saldo,
              SUM(CASE WHEN disponivel>0 AND carteira_quantidade>disponivel THEN carteira_valor ELSE 0 END) AS carteira_em_insuficiencia_com_saldo,
              SUM(CASE WHEN sinalizado THEN carteira_valor ELSE 0 END) AS carteira_nos_pares_sinalizados
              FROM situacao LIMIT 1""")
            totals = dict(zip([x[0] for x in cur.description], cur.fetchone()))
            cur = con.execute(PENDING + f"""SELECT s.produto_id,s.centro_id,p.codigo AS produto,
              c.codigo AS centro,s.unidade,s.disponivel,s.carteira_quantidade,s.carteira_valor
              FROM situacao s JOIN produtos p ON p.id=s.produto_id
              JOIN centros c ON c.id=s.centro_id WHERE {condition}
              ORDER BY s.carteira_valor DESC,s.produto_id,s.centro_id LIMIT 20""")
            rows = [dict(zip([x[0] for x in cur.description], row)) for row in cur.fetchall()]
        return {'totais':totals, 'prioridades_amostra':rows,'escopo_prioridades':scope,
                'natureza':'Ruptura observada = disponível zero; insuficiência com saldo positivo = carteira maior que disponível. '
                           'O grupo amplo sinalizados é a união, não sinônimo de ruptura. Categorias mutuamente exclusivas. '
                           'por produto/centro e mesma unidade. Não é previsão estatística nem score ML. '
                           'Estoque é fotografia independente; carteira não é perda estimada.'}

    @observe('duckdb.rupture_impact')
    def rupture_impact(self):
        """Impacto completo em saldo zero: EXISTS não multiplica itens por posições."""
        with duckdb.connect(str(self.database),read_only=True) as con:
            cur=con.execute("""SELECT COUNT(*) AS linhas_pendentes,
              COUNT(DISTINCT v.pedido_id) AS pedidos_distintos,
              COALESCE(SUM(v.receita_liquida),0) AS carteira_pendente,
              COALESCE(SUM(v.custo_total),0) AS custo_carteira,
              COALESCE(SUM(v.receita_liquida-v.custo_total),0) AS margem_carteira,
              ROUND(100*SUM(v.receita_liquida-v.custo_total)/NULLIF(SUM(v.receita_liquida),0),4) AS margem_pct
              FROM vendas v WHERE v.status='pendente' AND EXISTS (
                SELECT 1 FROM estoque e WHERE e.produto_id=v.produto_id
                AND e.centro_id=v.centro_id AND e.disponivel=0) LIMIT 1""")
            result=dict(zip([x[0] for x in cur.description],cur.fetchone()))
        return {'escopo':'todos os pares com disponível zero; não apenas os 20 prioritários',
                'totais':result,'natureza':'Valores da carteira, não faturamento, perda comprovada ou previsão ML.'}

    def commercial(self, question):
        return select_commercial_context(commercial_snapshot(self.database), question)

    @observe('duckdb.commercial_impact')
    def commercial_impact(self, pairs):
        pairs = list(dict.fromkeys(tuple(pair) for pair in pairs))
        if not pairs:
            return {'escopo':'amostra sem pares', 'por_familia':[]}
        if len(pairs)>20 or any(len(pair)!=2 or any(type(v) is not int or not 0<v<10**9 for v in pair) for pair in pairs):
            raise ValueError('Pares inválidos ou limite excedido.')
        # Apenas placeholders são construídos. Nenhum texto livre vira SQL.
        placeholders = ','.join(['(?,?)']*len(pairs))
        sql = f"""WITH selecionados(produto_id,centro_id) AS (VALUES {placeholders})
          SELECT p.categoria,v.unidade,COUNT(*) AS linhas_pendentes,COUNT(DISTINCT v.pedido_id) AS pedidos,
          SUM(v.receita_liquida) AS carteira_pendente,SUM(v.margem_valor) AS margem_carteira
          FROM vendas v JOIN selecionados s USING(produto_id,centro_id)
          JOIN produtos p ON p.id=v.produto_id WHERE v.status='pendente'
          GROUP BY p.categoria,v.unidade ORDER BY carteira_pendente DESC,p.categoria,v.unidade LIMIT 20"""
        with duckdb.connect(str(self.database), read_only=True) as con:
            cur=con.execute(sql,[value for pair in pairs for value in pair])
            rows=[dict(zip([x[0] for x in cur.description],row)) for row in cur.fetchall()]
        return {'escopo':'somente os até 20 pares priorizados pelo agente de estoque; não é total global',
                'pares_consultados':len(pairs), 'por_familia':rows}

    def documents(self, question):
        if self.index is None:
            raise RuntimeError('Índice indisponível')
        self.index.synchronize()
        return self.index.search(question)

    def backorder(self, question):
        try:
            features=parse_features(question)
        except MLInputError as error:
            return {'status':'needs_input','message':str(error),
                    'natureza':'Nenhuma previsão executada; atributos não serão inferidos do DuckDB.'}
        return {'status':'predicted', **predict_risk(features),
                'natureza':'Modelo scikit-learn público externo; score não calibrado, não validado no agro local.'}
