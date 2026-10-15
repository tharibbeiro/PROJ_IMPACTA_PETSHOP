/* =========================================================
   Pet Shop Patas & Cia - Criação das tabelas (SQL Server)

   Modelo:
     Categorias (1) ──< Produtos
     Clientes   (1) ──< Pets
     Clientes   (1) ──< Vendas (1) ──< ItensVenda
     ItensVenda referencia UM produto OU UM serviço (e o pet, quando for serviço)

   Para usar outro nome de banco, troque "PetShop_Patas_Cia" neste arquivo
   e no 02_inserir_dados.sql (ou rode data/gerar_dados.py de novo).
   ========================================================= */

IF DB_ID('PetShop_Patas_Cia') IS NULL
BEGIN
    CREATE DATABASE PetShop_Patas_Cia;
END
GO

USE PetShop_Patas_Cia;
GO

-- Limpa tudo se já existir (permite rodar o script de novo sem erro)
IF OBJECT_ID('dbo.vw_VendasResumo', 'V') IS NOT NULL DROP VIEW dbo.vw_VendasResumo;
IF OBJECT_ID('dbo.ItensVenda', 'U') IS NOT NULL DROP TABLE dbo.ItensVenda;
IF OBJECT_ID('dbo.Vendas', 'U') IS NOT NULL DROP TABLE dbo.Vendas;
IF OBJECT_ID('dbo.Pets', 'U') IS NOT NULL DROP TABLE dbo.Pets;
IF OBJECT_ID('dbo.Clientes', 'U') IS NOT NULL DROP TABLE dbo.Clientes;
IF OBJECT_ID('dbo.Servicos', 'U') IS NOT NULL DROP TABLE dbo.Servicos;
IF OBJECT_ID('dbo.Produtos', 'U') IS NOT NULL DROP TABLE dbo.Produtos;
IF OBJECT_ID('dbo.Categorias', 'U') IS NOT NULL DROP TABLE dbo.Categorias;
GO

CREATE TABLE dbo.Categorias (
    CategoriaID   INT IDENTITY(1,1) PRIMARY KEY,
    Nome          NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE dbo.Produtos (
    ProdutoID     INT IDENTITY(1,1) PRIMARY KEY,
    Nome          NVARCHAR(150) NOT NULL,
    CategoriaID   INT NOT NULL,
    Preco         DECIMAL(10,2) NOT NULL,
    Estoque       INT NOT NULL DEFAULT 0,
    CONSTRAINT FK_Produtos_Categorias FOREIGN KEY (CategoriaID)
        REFERENCES dbo.Categorias(CategoriaID)
);
GO

CREATE TABLE dbo.Servicos (
    ServicoID     INT IDENTITY(1,1) PRIMARY KEY,
    Nome          NVARCHAR(100) NOT NULL,
    Preco         DECIMAL(10,2) NOT NULL
);
GO

CREATE TABLE dbo.Clientes (
    ClienteID     INT IDENTITY(1,1) PRIMARY KEY,
    Nome          NVARCHAR(150) NOT NULL,
    Email         NVARCHAR(150) NOT NULL,
    Bairro        NVARCHAR(100) NOT NULL,
    Cidade        NVARCHAR(100) NOT NULL,
    DataCadastro  DATE NOT NULL
);
GO

CREATE TABLE dbo.Pets (
    PetID           INT IDENTITY(1,1) PRIMARY KEY,
    ClienteID       INT NOT NULL,
    Nome            NVARCHAR(80) NOT NULL,
    Especie         NVARCHAR(30) NOT NULL,
    Raca            NVARCHAR(60) NOT NULL,
    DataNascimento  DATE NOT NULL,
    CONSTRAINT FK_Pets_Clientes FOREIGN KEY (ClienteID)
        REFERENCES dbo.Clientes(ClienteID)
);
GO

CREATE TABLE dbo.Vendas (
    VendaID         INT IDENTITY(1,1) PRIMARY KEY,
    ClienteID       INT NOT NULL,
    DataVenda       DATE NOT NULL,
    FormaPagamento  NVARCHAR(30) NOT NULL,  -- Pix, Cartão de Crédito, Cartão de Débito, Dinheiro
    Status          NVARCHAR(20) NOT NULL,  -- Pago, Pendente, Cancelado
    CONSTRAINT FK_Vendas_Clientes FOREIGN KEY (ClienteID)
        REFERENCES dbo.Clientes(ClienteID)
);
GO

CREATE TABLE dbo.ItensVenda (
    ItemID          INT IDENTITY(1,1) PRIMARY KEY,
    VendaID         INT NOT NULL,
    ProdutoID       INT NULL,   -- preenchido quando o item é um produto
    ServicoID       INT NULL,   -- preenchido quando o item é um serviço
    PetID           INT NULL,   -- pet atendido (só para serviços)
    Quantidade      INT NOT NULL,
    PrecoUnitario   DECIMAL(10,2) NOT NULL,
    CONSTRAINT FK_ItensVenda_Vendas   FOREIGN KEY (VendaID)   REFERENCES dbo.Vendas(VendaID),
    CONSTRAINT FK_ItensVenda_Produtos FOREIGN KEY (ProdutoID) REFERENCES dbo.Produtos(ProdutoID),
    CONSTRAINT FK_ItensVenda_Servicos FOREIGN KEY (ServicoID) REFERENCES dbo.Servicos(ServicoID),
    CONSTRAINT FK_ItensVenda_Pets     FOREIGN KEY (PetID)     REFERENCES dbo.Pets(PetID),
    -- cada item é um produto OU um serviço, nunca os dois nem nenhum
    CONSTRAINT CK_ItensVenda_ProdutoOuServico CHECK (
        (ProdutoID IS NOT NULL AND ServicoID IS NULL) OR
        (ProdutoID IS NULL AND ServicoID IS NOT NULL)
    )
);
GO

-- View de apoio: vendas com valor total já calculado
CREATE OR ALTER VIEW dbo.vw_VendasResumo AS
SELECT
    v.VendaID,
    c.Nome        AS Cliente,
    c.Bairro,
    v.DataVenda,
    v.FormaPagamento,
    v.Status,
    SUM(i.Quantidade * i.PrecoUnitario) AS ValorTotal
FROM dbo.Vendas v
JOIN dbo.Clientes c   ON c.ClienteID = v.ClienteID
JOIN dbo.ItensVenda i ON i.VendaID = v.VendaID
GROUP BY v.VendaID, c.Nome, c.Bairro, v.DataVenda, v.FormaPagamento, v.Status;
GO
