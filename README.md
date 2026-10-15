# Patas & Cia — BI de Pet Shop

Projeto de faculdade de dados/BI: pet shop fictício que vende produtos (ração,
petiscos, brinquedos...) e serviços (banho, tosa, consulta veterinária, hotel),
com 3 camadas — banco de dados, back-end e front-end.

<img width="1315" height="737" alt="image" src="https://github.com/user-attachments/assets/aa576e6d-67b4-4b35-9e93-9831f3117108" />


## Arquitetura

```
SQL Server (dbo.*)  →  Python (backend/processar_metricas.py)  →  SQL Server (analytics.*)  →  Power BI
   dado bruto              aplica regras de negócio                  dado tratado               dashboard
```

## Modelo de dados

```
Categorias (1) ──< Produtos
Clientes (1) ──< Pets
Clientes (1) ──< Vendas (1) ──< ItensVenda >── Produtos | Servicos (um OU outro)
                                      └──── Pets (quando o item é um serviço)
```

Um mesmo pedido pode misturar produtos e serviços. A tabela `ItensVenda` guarda os
dois tipos, com uma regra (`CHECK`) que garante que cada item seja produto **ou**
serviço, nunca os dois.

## Estrutura do repositório

```
sql/
├── 01_criar_tabelas.sql        -- cria o banco PetShop_Patas_Cia e as tabelas
├── 02_inserir_dados.sql        -- popula com dados fictícios
└── 03_consultas_validacao.sql  -- conferência da carga
backend/
├── processar_metricas.py       -- calcula as métricas e grava em analytics.*
├── requirements.txt
└── .env.example                -- copie para .env e configure sua conexão
data/
├── gerar_dados.py              -- gera o 02_inserir_dados.sql (Faker)
└── requirements.txt
dashboard/
└── (arquivo .pbix do Power BI)
docs/
├── guia_dashboard.md           -- layout e passo a passo do painel
└── roteiro_video.md            -- roteiro do vídeo de demonstração
```

## Como rodar

1. **Banco de dados**: no SSMS, rode `sql/01_criar_tabelas.sql`, depois
   `sql/02_inserir_dados.sql` e confira com `sql/03_consultas_validacao.sql`.
2. **Back-end**:
   ```bash
   cd backend
   pip install -r requirements.txt
   copy .env.example .env      # (Windows) e edite o SQL_SERVER com o nome do seu servidor
   python processar_metricas.py
   ```
3. **Dashboard**: no Power BI Desktop, conecte no SQL Server, banco
   `PetShop_Patas_Cia`, e selecione apenas as tabelas do schema **analytics**
   (veja `docs/guia_dashboard.md`).

Para gerar outro conjunto de dados: `cd data && pip install -r requirements.txt && python gerar_dados.py`.

## Regras de negócio aplicadas no back-end

- Vendas **canceladas não entram** no faturamento, no ticket médio nem nos rankings;
  elas aparecem só em `VendasPorStatus` e na taxa de cancelamento.
- **Ticket médio** = faturamento ÷ número de vendas válidas.
- **Cliente recorrente** = cliente com 2 ou mais vendas válidas.

## Tabelas geradas (schema `analytics`)

| Tabela | O que traz |
|---|---|
| `KPIsGerais` | 1 linha: faturamento, vendas, ticket médio, clientes, pets, taxa de cancelamento |
| `FaturamentoMensal` | faturamento por mês (`MesInicio` para ordenar o eixo) |
| `ReceitaPorTipo` | produtos x serviços |
| `FaturamentoPorCategoria` | por categoria (serviços entram como "Serviços") |
| `TopProdutos` / `TopServicos` | top 10 de cada |
| `VendasPorFormaPagamento` | Pix, crédito, débito, dinheiro |
| `VendasPorStatus` | Pago, Pendente, Cancelado |
| `VendasPorBairro` | faturamento por bairro do cliente |
| `ResumoPorEspecie` | pets cadastrados x atendimentos por espécie |
| `TicketMedioPorCliente` | ticket médio e total por cliente |
| `ClientesRecorrentes` | top 10 clientes com 2+ vendas |

