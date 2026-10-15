"""
Back-end - processamento de métricas do pet shop Patas & Cia.

Conecta no SQL Server (PetShop_Patas_Cia), lê as tabelas transacionais em dbo.*
(Categorias, Produtos, Servicos, Clientes, Pets, Vendas, ItensVenda), aplica as
regras de negócio com pandas e grava o resultado em tabelas agregadas no schema
`analytics`. O Power BI deve conectar SOMENTE nessas tabelas, nunca direto no dbo.

Regra de negócio principal: vendas com status "Cancelado" NÃO entram no
faturamento, no ticket médio nem nos rankings. Elas só aparecem em
VendasPorStatus e na taxa de cancelamento.

Tabelas geradas (schema analytics):
    - KPIsGerais                (1 linha: faturamento, ticket médio, vendas, clientes...)
    - FaturamentoMensal         (MesInicio, AnoMes, Faturamento)
    - ReceitaPorTipo            (Tipo [Produto/Serviço], Faturamento)
    - FaturamentoPorCategoria   (Categoria, Faturamento, QtdItens) - serviços = "Serviços"
    - TopProdutos               (Produto, Categoria, Faturamento, QtdVendida) - top 10
    - TopServicos               (Servico, Faturamento, QtdRealizada) - top 10
    - VendasPorFormaPagamento   (FormaPagamento, QtdVendas, Faturamento)
    - VendasPorStatus           (Status, QtdVendas)
    - VendasPorBairro           (Bairro, QtdVendas, Faturamento)
    - ResumoPorEspecie          (Especie, QtdPets, QtdAtendimentos, FaturamentoServicos)
    - TicketMedioPorCliente     (ClienteID, Cliente, QtdVendas, Faturamento, TicketMedio)
    - ClientesRecorrentes       (ClienteID, Cliente, QtdVendas, Faturamento) - top 10

Configuração:
    Copie .env.example para .env e preencha com os dados da sua instância.

Uso:
    python processar_metricas.py
"""

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

SERVER = os.environ.get("SQL_SERVER", "")      # ex: localhost ou localhost\SQLEXPRESS
DATABASE = os.environ.get("SQL_DATABASE", "PetShop_Patas_Cia")
DRIVER = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
TRUSTED_CONNECTION = os.environ.get("SQL_TRUSTED_CONNECTION", "yes")
USERNAME = os.environ.get("SQL_USERNAME", "")
PASSWORD = os.environ.get("SQL_PASSWORD", "")

TABELAS_BRUTAS = ["Categorias", "Produtos", "Servicos", "Clientes", "Pets", "Vendas", "ItensVenda"]


def get_engine():
    """Monta a connection string. Suporta autenticação Windows ou SQL Server."""
    if not SERVER:
        raise SystemExit("Defina SQL_SERVER no arquivo .env (copie o .env.example).")
    driver_fmt = DRIVER.replace(" ", "+")
    if TRUSTED_CONNECTION.lower() == "yes":
        conn_str = (f"mssql+pyodbc://{SERVER}/{DATABASE}"
                    f"?driver={driver_fmt}&trusted_connection=yes")
    else:
        conn_str = (f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}"
                    f"?driver={driver_fmt}")
    return create_engine(conn_str)


def criar_schema_analytics(engine):
    with engine.begin() as conn:
        conn.execute(text(
            "IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'analytics') "
            "EXEC('CREATE SCHEMA analytics')"
        ))


def carregar_dados_brutos(engine) -> dict:
    dfs = {t: pd.read_sql(f"SELECT * FROM dbo.{t}", engine) for t in TABELAS_BRUTAS}
    # DECIMAL chega do SQL Server como objeto Decimal; convertemos para float
    dfs["ItensVenda"]["PrecoUnitario"] = dfs["ItensVenda"]["PrecoUnitario"].astype(float)
    return dfs


def montar_base_unificada(dfs: dict) -> pd.DataFrame:
    """Uma linha por item vendido, já com produto/serviço, categoria, pet e cliente."""
    itens = dfs["ItensVenda"].copy()
    itens["ValorItem"] = itens["Quantidade"] * itens["PrecoUnitario"]

    produtos = (
        dfs["Produtos"].merge(dfs["Categorias"].rename(columns={"Nome": "Categoria"}), on="CategoriaID")
        [["ProdutoID", "Nome", "Categoria"]].rename(columns={"Nome": "ProdutoNome"})
    )
    servicos = dfs["Servicos"][["ServicoID", "Nome"]].rename(columns={"Nome": "ServicoNome"})
    pets = dfs["Pets"][["PetID", "Especie"]]
    clientes = dfs["Clientes"][["ClienteID", "Nome", "Bairro"]].rename(columns={"Nome": "Cliente"})

    base = itens.merge(dfs["Vendas"], on="VendaID", how="left")
    base = base.merge(produtos, on="ProdutoID", how="left")
    base = base.merge(servicos, on="ServicoID", how="left")
    base = base.merge(pets, on="PetID", how="left")
    base = base.merge(clientes, on="ClienteID", how="left")

    base["Tipo"] = np.where(base["ProdutoID"].notna(), "Produto", "Serviço")
    base["Descricao"] = base["ProdutoNome"].fillna(base["ServicoNome"])
    base["Categoria"] = base["Categoria"].fillna("Serviços")
    base["DataVenda"] = pd.to_datetime(base["DataVenda"])
    base["AnoMes"] = base["DataVenda"].dt.strftime("%Y-%m")
    # data do 1º dia do mês: é ela que o Power BI usa para ordenar o eixo do tempo
    base["MesInicio"] = base["DataVenda"].dt.to_period("M").dt.to_timestamp().dt.date
    return base


def calcular_metricas(dfs: dict, base: pd.DataFrame) -> dict:
    vendas, pets = dfs["Vendas"], dfs["Pets"]
    validas = base[base["Status"] != "Cancelado"]  # regra: cancelada não conta
    m = {}

    # ---- por cliente (base para ticket médio e recorrência)
    por_venda = validas.groupby(["VendaID", "ClienteID", "Cliente"], as_index=False)["ValorItem"].sum()
    por_cliente = (
        por_venda.groupby(["ClienteID", "Cliente"], as_index=False)
        .agg(QtdVendas=("VendaID", "nunique"), Faturamento=("ValorItem", "sum"))
    )
    por_cliente["TicketMedio"] = por_cliente["Faturamento"] / por_cliente["QtdVendas"]

    # ---- 1) KPIs gerais (uma linha só: no Power BI a soma de 1 linha é o próprio valor)
    faturamento_total = validas["ValorItem"].sum()
    total_vendas = validas["VendaID"].nunique()
    m["KPIsGerais"] = pd.DataFrame([{
        "FaturamentoTotal": faturamento_total,
        "TotalVendas": total_vendas,
        "TicketMedio": faturamento_total / total_vendas,
        "ClientesAtivos": len(por_cliente),
        "ClientesRecorrentes": int((por_cliente["QtdVendas"] >= 2).sum()),
        "TotalPets": len(pets),
        "ReceitaProdutos": validas.loc[validas["Tipo"] == "Produto", "ValorItem"].sum(),
        "ReceitaServicos": validas.loc[validas["Tipo"] == "Serviço", "ValorItem"].sum(),
        "TaxaCancelamentoPct": (vendas["Status"] == "Cancelado").mean() * 100,
    }])

    # ---- 2) Faturamento mensal
    m["FaturamentoMensal"] = (
        validas.groupby(["MesInicio", "AnoMes"], as_index=False)["ValorItem"].sum()
        .rename(columns={"ValorItem": "Faturamento"})
        .sort_values("MesInicio").reset_index(drop=True)
    )

    # ---- 3) Receita produto x serviço
    m["ReceitaPorTipo"] = (
        validas.groupby("Tipo", as_index=False)["ValorItem"].sum()
        .rename(columns={"ValorItem": "Faturamento"})
        .sort_values("Faturamento", ascending=False).reset_index(drop=True)
    )

    # ---- 4) Faturamento por categoria (serviços entram como categoria "Serviços")
    m["FaturamentoPorCategoria"] = (
        validas.groupby("Categoria", as_index=False)
        .agg(Faturamento=("ValorItem", "sum"), QtdItens=("Quantidade", "sum"))
        .sort_values("Faturamento", ascending=False).reset_index(drop=True)
    )

    # ---- 5) Top 10 produtos
    m["TopProdutos"] = (
        validas[validas["Tipo"] == "Produto"]
        .groupby(["Descricao", "Categoria"], as_index=False)
        .agg(Faturamento=("ValorItem", "sum"), QtdVendida=("Quantidade", "sum"))
        .rename(columns={"Descricao": "Produto"})
        .sort_values("Faturamento", ascending=False).head(10).reset_index(drop=True)
    )

    # ---- 6) Top 10 serviços
    m["TopServicos"] = (
        validas[validas["Tipo"] == "Serviço"]
        .groupby("Descricao", as_index=False)
        .agg(Faturamento=("ValorItem", "sum"), QtdRealizada=("Quantidade", "sum"))
        .rename(columns={"Descricao": "Servico"})
        .sort_values("Faturamento", ascending=False).head(10).reset_index(drop=True)
    )

    # ---- 7) Formas de pagamento
    m["VendasPorFormaPagamento"] = (
        validas.groupby("FormaPagamento", as_index=False)
        .agg(QtdVendas=("VendaID", "nunique"), Faturamento=("ValorItem", "sum"))
        .sort_values("Faturamento", ascending=False).reset_index(drop=True)
    )

    # ---- 8) Status das vendas (aqui as canceladas aparecem)
    m["VendasPorStatus"] = (
        vendas.groupby("Status").size().reset_index(name="QtdVendas")
        .sort_values("QtdVendas", ascending=False).reset_index(drop=True)
    )

    # ---- 9) Bairros
    m["VendasPorBairro"] = (
        validas.groupby("Bairro", as_index=False)
        .agg(QtdVendas=("VendaID", "nunique"), Faturamento=("ValorItem", "sum"))
        .sort_values("Faturamento", ascending=False).reset_index(drop=True)
    )

    # ---- 10) Resumo por espécie (pets cadastrados x atendimentos)
    atendimentos = (
        validas[validas["Tipo"] == "Serviço"].groupby("Especie", as_index=False)
        .agg(QtdAtendimentos=("ItemID", "count"), FaturamentoServicos=("ValorItem", "sum"))
    )
    resumo = pets.groupby("Especie", as_index=False).agg(QtdPets=("PetID", "count"))
    m["ResumoPorEspecie"] = (
        resumo.merge(atendimentos, on="Especie", how="left").fillna(0)
        .sort_values("QtdPets", ascending=False).reset_index(drop=True)
    )
    m["ResumoPorEspecie"]["QtdAtendimentos"] = m["ResumoPorEspecie"]["QtdAtendimentos"].astype(int)

    # ---- 11) Ticket médio por cliente
    m["TicketMedioPorCliente"] = por_cliente.sort_values("TicketMedio", ascending=False).reset_index(drop=True)

    # ---- 12) Top 10 clientes recorrentes (2+ vendas)
    m["ClientesRecorrentes"] = (
        por_cliente[por_cliente["QtdVendas"] >= 2]
        .sort_values(["QtdVendas", "Faturamento"], ascending=False)
        .head(10)[["ClienteID", "Cliente", "QtdVendas", "Faturamento"]]
        .reset_index(drop=True)
    )

    for df in m.values():  # valores monetários com 2 casas
        for col in df.select_dtypes("float").columns:
            df[col] = df[col].round(2)
    return m


def gravar_metricas(engine, metricas: dict):
    for nome_tabela, df in metricas.items():
        df.to_sql(nome_tabela, engine, schema="analytics", if_exists="replace", index=False)
        print(f"  -> analytics.{nome_tabela}: {len(df)} linhas gravadas")


def main():
    engine = get_engine()
    print(f"Conectado em {SERVER}/{DATABASE}")

    criar_schema_analytics(engine)

    dfs = carregar_dados_brutos(engine)
    print(f"Dados brutos carregados: {len(dfs['Vendas'])} vendas, {len(dfs['ItensVenda'])} itens, "
          f"{len(dfs['Clientes'])} clientes, {len(dfs['Pets'])} pets")

    base = montar_base_unificada(dfs)
    metricas = calcular_metricas(dfs, base)

    print("Gravando métricas em analytics.*:")
    gravar_metricas(engine, metricas)

    print("\nConcluído. No Power BI, conecte no SQL Server e use as tabelas do schema 'analytics'.")


if __name__ == "__main__":
    main()
