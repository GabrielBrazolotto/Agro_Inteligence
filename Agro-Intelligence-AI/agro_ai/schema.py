"""Schema v2: chaves e campos legados preservados; novas relações explícitas."""
SCHEMA_VERSION = 2
SCHEMA = """
CREATE TABLE regioes (
 id INTEGER PRIMARY KEY, codigo VARCHAR UNIQUE NOT NULL, nome VARCHAR NOT NULL,
 estado VARCHAR NOT NULL, peso_comercial DOUBLE NOT NULL CHECK(peso_comercial > 0));
CREATE TABLE centros (
 id INTEGER PRIMARY KEY, codigo VARCHAR UNIQUE NOT NULL, nome VARCHAR NOT NULL,
 regiao_id INTEGER NOT NULL REFERENCES regioes(id));
CREATE TABLE clientes (
 id INTEGER PRIMARY KEY, codigo VARCHAR UNIQUE NOT NULL, nome VARCHAR NOT NULL,
 cidade VARCHAR NOT NULL, estado VARCHAR NOT NULL, regiao_id INTEGER NOT NULL REFERENCES regioes(id));
CREATE TABLE produtos (
 id INTEGER PRIMARY KEY, codigo VARCHAR UNIQUE NOT NULL, nome VARCHAR NOT NULL,
 categoria VARCHAR NOT NULL, unidade VARCHAR NOT NULL,
 preco_lista DECIMAL(18,2) NOT NULL CHECK(preco_lista>0),
 custo_unitario DECIMAL(18,2) NOT NULL CHECK(custo_unitario>0), fabricante VARCHAR NOT NULL);
CREATE TABLE historico_precos (
 id INTEGER PRIMARY KEY, produto_id INTEGER NOT NULL REFERENCES produtos(id),
 data_referencia DATE NOT NULL, preco_lista DECIMAL(18,2) NOT NULL CHECK(preco_lista>0),
 custo_unitario DECIMAL(18,2) NOT NULL CHECK(custo_unitario>0), UNIQUE(produto_id,data_referencia));
CREATE TABLE pedidos (
 id INTEGER PRIMARY KEY, codigo VARCHAR UNIQUE NOT NULL,
 cliente_id INTEGER NOT NULL REFERENCES clientes(id), centro_id INTEGER NOT NULL REFERENCES centros(id),
 regiao_id INTEGER NOT NULL REFERENCES regioes(id), data_pedido DATE NOT NULL,
 vencimento DATE NOT NULL CHECK(vencimento>data_pedido),
 status VARCHAR NOT NULL CHECK(status IN ('faturado','pendente','cancelado')),
 valor_liquido DECIMAL(18,2) NOT NULL CHECK(valor_liquido>0));
CREATE TABLE vendas (
 id INTEGER PRIMARY KEY, pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
 cliente_id INTEGER NOT NULL REFERENCES clientes(id), produto_id INTEGER NOT NULL REFERENCES produtos(id),
 centro_id INTEGER NOT NULL REFERENCES centros(id), regiao_id INTEGER NOT NULL REFERENCES regioes(id),
 data_venda DATE NOT NULL, vencimento DATE NOT NULL CHECK(vencimento>data_venda),
 quantidade INTEGER NOT NULL CHECK(quantidade>0), unidade VARCHAR NOT NULL,
 preco_lista DECIMAL(18,2) NOT NULL CHECK(preco_lista>0),
 custo_unitario DECIMAL(18,2) NOT NULL CHECK(custo_unitario>0),
 desconto_pct DECIMAL(8,4) NOT NULL CHECK(desconto_pct BETWEEN 0 AND 18),
 preco_unitario DECIMAL(18,2) NOT NULL CHECK(preco_unitario>0),
 receita_bruta DECIMAL(18,2) NOT NULL CHECK(receita_bruta>0),
 desconto_valor DECIMAL(18,2) NOT NULL CHECK(desconto_valor>=0),
 receita_liquida DECIMAL(18,2) NOT NULL CHECK(receita_liquida>0),
 custo_total DECIMAL(18,2) NOT NULL CHECK(custo_total>0),
 margem_valor DECIMAL(18,2) NOT NULL, margem_pct DECIMAL(8,4) NOT NULL,
 status VARCHAR NOT NULL CHECK(status IN ('faturada','pendente','cancelada')), cenario VARCHAR NOT NULL);
CREATE TABLE estoque (
 id INTEGER PRIMARY KEY, produto_id INTEGER NOT NULL REFERENCES produtos(id),
 centro_id INTEGER NOT NULL REFERENCES centros(id), data_referencia DATE NOT NULL, unidade VARCHAR NOT NULL,
 quantidade INTEGER NOT NULL CHECK(quantidade>=0), reservado INTEGER NOT NULL CHECK(reservado>=0),
 disponivel INTEGER NOT NULL CHECK(disponivel=quantidade-reservado AND disponivel>=0),
 estoque_minimo INTEGER NOT NULL CHECK(estoque_minimo>=0),
 estoque_maximo INTEGER NOT NULL CHECK(estoque_maximo>estoque_minimo),
 custo_unitario DECIMAL(18,2) NOT NULL CHECK(custo_unitario>0), cenario VARCHAR NOT NULL,
 UNIQUE(produto_id,centro_id));
CREATE TABLE dataset_metadata (signature VARCHAR PRIMARY KEY, schema_version INTEGER NOT NULL);
"""
