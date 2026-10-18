"""Cooperativa inteiramente fictícia. Geração determinística sem acesso a APIs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

from faker import Faker
import numpy as np
import pandas as pd

SEED = 20261015
START = '2025-10-01'
END = '2026-09-30'
TABLES = ('regioes', 'centros', 'clientes', 'produtos', 'historico_precos',
          'pedidos', 'vendas', 'estoque')


def generate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    fake = Faker('pt_BR')
    fake.seed_instance(seed)
    frames = {}
    frames['regioes'] = pd.DataFrame([
        (1, 'REG-01', 'Oeste Simulado', 'PR', 0.45),
        (2, 'REG-02', 'Centro Simulado', 'PR', 0.25),
        (3, 'REG-03', 'Vale Simulado', 'SC', 0.15),
        (4, 'REG-04', 'Sul Simulado', 'RS', 0.10),
        (5, 'REG-05', 'Cerrado Simulado', 'MS', 0.05),
    ], columns=['id', 'codigo', 'nome', 'estado', 'peso_comercial'])
    frames['centros'] = pd.DataFrame([
        (i, f'CTR-{i:03}', f'Centro Fictício {i:02}', (i - 1) // 3 + 1)
        for i in range(1, 16)
    ], columns=['id', 'codigo', 'nome', 'regiao_id'])
    weights = frames['regioes']['peso_comercial'].to_numpy()
    regions = rng.choice(np.arange(1, 6), 5000, p=weights)
    frames['clientes'] = pd.DataFrame([
        (i, f'CLI-{i:06}', f'Cooperado Fictício {i:05} {fake.last_name()}',
         f'Município Sintético {int(region):02}',
         frames['regioes'].iloc[int(region)-1]['estado'], int(region))
        for i, region in enumerate(regions, 1)
    ], columns=['id', 'codigo', 'nome', 'cidade', 'estado', 'regiao_id'])
    families = ['Fertilizantes', 'Agroquímicos', 'Sementes de soja',
                'Sementes de milho', 'Nutrição foliar']
    products = []
    for i in range(1, 1001):
        family = (i - 1) // 200
        unit = (('KG' if i % 2 else 'tonelada') if family == 0 else
                'saca_40KG' if family == 2 else 'saca_20KG' if family == 3 else 'L')
        low, high = {'KG': (2, 6), 'tonelada': (2000, 6000), 'L': (25, 180),
                     'saca_40KG': (240, 440), 'saca_20KG': (450, 950)}[unit]
        price = int(rng.integers(low * 100, high * 100))
        cost = int(round(price * rng.uniform(.70, .85)))
        products.append((i, f'PRD-{i:05}', f'{families[family]} Fictício {i:04}',
                         families[family], unit, price / 100, cost / 100,
                         f'Fabricante Fictício {(i-1)%20+1:02}'))
    frames['produtos'] = pd.DataFrame(products, columns=[
        'id', 'codigo', 'nome', 'categoria', 'unidade', 'preco_lista', 'custo_unitario', 'fabricante'])
    # Histórico mensal por produto. Inteiros em centavos em todos os cálculos.
    months = pd.date_range(START, periods=12, freq='MS')
    prices, price_map = [], {}
    for month_index, date in enumerate(months):
        for product in products:
            pid = product[0]
            factor = 1 + .004 * month_index + .015 * np.sin(month_index)
            price = int(round(product[5] * 100 * factor))
            cost = int(round(product[6] * 100 * (1 + .003 * month_index)))
            price_map[pid, month_index] = (price, cost)
            prices.append((len(prices)+1, pid, date.date().isoformat(), price/100, cost/100))
    frames['historico_precos'] = pd.DataFrame(prices, columns=[
        'id', 'produto_id', 'data_referencia', 'preco_lista', 'custo_unitario'])
    # Probabilidades por mês: pico de compra de insumos antes do plantio (jul-out).
    month_weights = np.array([14, 9, 5, 4, 5, 5, 4, 4, 6, 10, 16, 18], dtype=float)
    month_weights /= month_weights.sum()
    orders = []
    for i in range(1, 8001):
        region = int(rng.choice(np.arange(1, 6), p=weights))
        candidates = np.flatnonzero(regions == region) + 1
        client = int(rng.choice(candidates))
        center = (region - 1) * 3 + int(rng.integers(1, 4))
        month = int(rng.choice(12, p=month_weights))
        date = months[month] + pd.Timedelta(days=int(rng.integers(0, months[month].days_in_month)))
        status = str(rng.choice(['faturado', 'pendente', 'cancelado'], p=[.72, .23, .05]))
        due = date + pd.Timedelta(days=int(rng.choice([30, 60, 90])))
        orders.append((i, f'PED-{i:06}', client, center, region, date.date().isoformat(),
                       due.date().isoformat(), status, month))
    # Cada pedido tem ao menos uma linha. Grão vendas = item de pedido, não nota fiscal.
    order_ids = np.concatenate([np.arange(1, 8001), rng.integers(1, 8001, 12000)])
    sales = []
    for sid, order_id in enumerate(order_ids, 1):
        order = orders[int(order_id)-1]
        region, month = order[4], order[8]
        # Cada produto é atendido pelos três centros de uma região; garante par em estoque.
        pid = int(rng.choice(np.arange(region, 1001, 5)))
        product = products[pid-1]
        unit = product[4]
        qlow, qhigh = {'KG': (500, 10001), 'tonelada': (1, 31), 'L': (5, 201),
                       'saca_40KG': (10, 301), 'saca_20KG': (5, 151)}[unit]
        quantity = int(rng.integers(qlow, qhigh))
        price, cost = price_map[pid, month]
        discount = int(rng.choice([0, 200, 300, 500, 800], p=[.25, .15, .20, .30, .10]))
        scenario = 'normal'
        if sid <= 100:
            discount, cost, scenario = 1800, int(round(price * .92)), 'desconto_elevado_margem_negativa'
        elif sid <= 200:
            discount, cost, scenario = 0, int(round(price * .60)), 'margem_alta'
        elif sid <= 300:
            discount, cost, scenario = 500, int(round(price * .95)), 'margem_comprimida'
        # Arredondamento half-up em centavos, sem erro acumulado de ponto flutuante.
        unit_price = (price * (10000 - discount) + 5000) // 10000
        if scenario == 'margem_comprimida':
            cost = unit_price  # Empate exato em centavos, inclusive em casos de meio centavo.
        gross = quantity * price
        net = quantity * unit_price
        total_cost = quantity * cost
        margin = net - total_cost
        margin_pct = round(100 * margin / net, 4)
        status = {'faturado': 'faturada', 'pendente': 'pendente', 'cancelado': 'cancelada'}[order[7]]
        sales.append((sid, int(order_id), order[2], pid, order[3], region,
                      order[5], order[6], quantity, unit, price/100, cost/100,
                      discount/100, unit_price/100, gross/100, (gross-net)/100,
                      net/100, total_cost/100, margin/100, margin_pct, status, scenario))
    frames['vendas'] = pd.DataFrame(sales, columns=[
        'id', 'pedido_id', 'cliente_id', 'produto_id', 'centro_id', 'regiao_id',
        'data_venda', 'vencimento', 'quantidade', 'unidade', 'preco_lista', 'custo_unitario',
        'desconto_pct', 'preco_unitario', 'receita_bruta', 'desconto_valor',
        'receita_liquida', 'custo_total', 'margem_valor', 'margem_pct', 'status', 'cenario'])
    order_frame = pd.DataFrame([order[:8] for order in orders], columns=[
        'id', 'codigo', 'cliente_id', 'centro_id', 'regiao_id', 'data_pedido', 'vencimento', 'status'])
    # Somar centavos, convertendo para reais somente ao gravar o total.
    cents = frames['vendas'][['pedido_id', 'receita_liquida']].copy()
    cents['centavos'] = (cents['receita_liquida'] * 100).round().astype('int64')
    order_frame['valor_liquido'] = order_frame['id'].map(cents.groupby('pedido_id')['centavos'].sum()) / 100
    frames['pedidos'] = order_frame
    stocks = []
    for product in products:
        pid = product[0]
        region = (pid - 1) % 5 + 1
        for center in range((region-1)*3+1, region*3+1):
            quantity = int(rng.integers(50, 800))
            reserved = int(rng.integers(0, quantity//3+1))
            minimum, maximum, scenario = 40, 1000, 'normal'
            if len(stocks) < 60:
                quantity, reserved, scenario = 0, 0, 'ruptura'
            elif len(stocks) < 120:
                quantity, reserved, scenario = 5000, 0, 'excesso'
            stocks.append((len(stocks)+1, pid, center, END, product[4], quantity,
                           reserved, quantity-reserved, minimum, maximum,
                           price_map[pid, 11][1]/100, scenario))
    frames['estoque'] = pd.DataFrame(stocks, columns=[
        'id', 'produto_id', 'centro_id', 'data_referencia', 'unidade', 'quantidade',
        'reservado', 'disponivel', 'estoque_minimo', 'estoque_maximo', 'custo_unitario', 'cenario'])
    return {name: frames[name] for name in TABLES}


def backup_csvs(directory: Path) -> Path | None:
    files = sorted(directory.glob('*.csv'))
    if not files:
        return None
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = directory.parent / 'backups' / f'antes-geracao-{stamp}'
    destination.mkdir(parents=True)
    for file in files:
        shutil.copy2(file, destination / file.name)
    return destination


def write_dataset(frames, directory: Path, seed=SEED):
    from agro_ai.validation import validate_frames
    report = validate_frames(frames)
    backup = backup_csvs(directory)
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, frame in frames.items():
        path = directory / f'{name}.csv'
        frame.to_csv(path, index=False, encoding='utf-8', float_format='%.4f', lineterminator='\n')
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'seed': seed, 'inicio': START, 'fim': END, 'ficticio': True,
                'counts': {key: len(value) for key, value in frames.items()},
                'sha256': hashes, 'validacao': report}
    (directory / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return backup, manifest
