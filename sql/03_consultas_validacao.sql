/* Consultas para conferir se a carga deu certo (rode depois do 02_inserir_dados.sql) */
USE PetShop_Patas_Cia;
GO

-- 1) Contagem de linhas por tabela (esperado: 7 / 44 / 12 / 120 / ~184 / 400 / ~770)
SELECT 'Categorias' AS Tabela, COUNT(*) AS Linhas FROM dbo.Categorias UNION ALL
SELECT 'Produtos',   COUNT(*) FROM dbo.Produtos   UNION ALL
SELECT 'Servicos',   COUNT(*) FROM dbo.Servicos   UNION ALL
SELECT 'Clientes',   COUNT(*) FROM dbo.Clientes   UNION ALL
SELECT 'Pets',       COUNT(*) FROM dbo.Pets       UNION ALL
SELECT 'Vendas',     COUNT(*) FROM dbo.Vendas     UNION ALL
SELECT 'ItensVenda', COUNT(*) FROM dbo.ItensVenda;

-- 2) Faturamento total sem as vendas canceladas
--    (deve ser igual ao FaturamentoTotal da tabela analytics.KPIsGerais depois de rodar o Python)
SELECT SUM(ValorTotal) AS FaturamentoSemCanceladas
FROM dbo.vw_VendasResumo
WHERE Status <> 'Cancelado';

-- 3) Produtos x serviços vendidos
SELECT CASE WHEN ProdutoID IS NOT NULL THEN 'Produto' ELSE 'Serviço' END AS Tipo,
       COUNT(*) AS Itens,
       SUM(Quantidade * PrecoUnitario) AS Valor
FROM dbo.ItensVenda
GROUP BY CASE WHEN ProdutoID IS NOT NULL THEN 'Produto' ELSE 'Serviço' END;
GO
