"""
Gera dados fictícios do pet shop Patas & Cia e escreve o script T-SQL
(sql/02_inserir_dados.sql) para rodar no SQL Server logo após o
01_criar_tabelas.sql.

Os dados seguem regras de negócio simples para ficarem coerentes:
    - cada cliente tem de 1 a 3 pets
    - vendas só acontecem depois da data de cadastro do cliente
    - serviços sempre vinculados a um pet do próprio cliente
    - preço do item = preço do catálogo (com desconto ocasional)
    - alguns clientes compram bem mais que outros (clientes recorrentes)

Uso:
    pip install -r requirements.txt
    python gerar_dados.py
"""

import os
import random
from datetime import date, timedelta

from faker import Faker

fake = Faker("pt_BR")
random.seed(42)
Faker.seed(42)

NOME_BANCO = "PetShop_Patas_Cia"
N_CLIENTES = 120
N_VENDAS = 400
HOJE = date.today()


def _inicio_janela(meses_atras: int = 11) -> date:
    """1º dia do mês de 'meses_atras' meses atrás -> série com meses completos (o atual fica parcial)."""
    total = HOJE.year * 12 + (HOJE.month - 1) - meses_atras
    return date(total // 12, total % 12 + 1, 1)


INICIO_JANELA = _inicio_janela()

# ---------------------------------------------------------------- catálogo
CATEGORIAS = [
    "Ração e Alimentação", "Petiscos e Snacks", "Brinquedos", "Higiene e Limpeza",
    "Acessórios e Passeio", "Camas e Casinhas", "Farmácia Pet",
]
PESO_CATEGORIA = [3, 2, 1.5, 2, 1, 0.7, 1.2]  # popularidade de cada categoria

PRODUTOS = {
    "Ração e Alimentação": [
        ("Ração Premium Cães Adultos 15kg", 189.90), ("Ração Premium Cães Filhotes 10kg", 154.90),
        ("Ração Super Premium Gatos Castrados 10kg", 219.90), ("Ração Gatos Adultos 3kg", 64.90),
        ("Ração Cães Raças Pequenas 7kg", 119.90), ("Sachê para Gatos 85g", 4.90),
        ("Alimento Úmido Cães 280g", 12.90),
    ],
    "Petiscos e Snacks": [
        ("Bifinho de Carne 65g", 9.90), ("Osso Nó Natural", 14.90), ("Palito Dental Cães c/7", 16.90),
        ("Petisco Gatos Atum 50g", 7.90), ("Biscoito Cães Premiados 250g", 18.90),
        ("Orelha de Boi Defumada", 11.90),
    ],
    "Brinquedos": [
        ("Bolinha de Borracha", 12.90), ("Mordedor de Corda", 15.90), ("Arranhador para Gatos", 89.90),
        ("Varinha com Penas", 19.90), ("Pelúcia com Apito", 24.90), ("Frisbee Resistente", 22.90),
    ],
    "Higiene e Limpeza": [
        ("Shampoo Neutro 500ml", 29.90), ("Condicionador Pelos Longos 500ml", 32.90),
        ("Tapete Higiênico c/30", 64.90), ("Areia Higiênica 4kg", 24.90),
        ("Escova Removedora de Pelos", 27.90), ("Lenço Umedecido Pet c/50", 18.90),
        ("Perfume Pet 120ml", 34.90),
    ],
    "Acessórios e Passeio": [
        ("Coleira Ajustável M", 34.90), ("Guia Retrátil 5m", 59.90), ("Peitoral Acolchoado G", 49.90),
        ("Comedouro de Inox", 26.90), ("Bebedouro Fonte Automático", 119.90),
        ("Caixa de Transporte M", 149.90), ("Roupinha de Moletom", 39.90),
    ],
    "Camas e Casinhas": [
        ("Cama Pet Média", 99.90), ("Casinha Plástica G", 189.90), ("Almofada Antiderrapante", 79.90),
        ("Cobertor Pet Soft", 44.90), ("Toca para Gatos", 69.90),
    ],
    "Farmácia Pet": [
        ("Antipulgas Cães 10-20kg", 89.90), ("Vermífugo para Gatos", 39.90),
        ("Suplemento Vitamínico 60 comp.", 74.90), ("Colírio de Limpeza Ocular", 29.90),
        ("Antipulgas Gatos", 79.90), ("Pomada Cicatrizante", 34.90),
    ],
}

SERVICOS = [
    ("Banho Pequeno Porte", 50.00), ("Banho Médio Porte", 70.00), ("Banho Grande Porte", 90.00),
    ("Tosa Higiênica", 40.00), ("Tosa Completa", 80.00), ("Corte de Unhas", 25.00),
    ("Consulta Veterinária", 150.00), ("Vacina V10", 120.00), ("Vacina Antirrábica", 70.00),
    ("Vermifugação", 45.00), ("Hotel Pet (diária)", 90.00), ("Day Care", 60.00),
]
PESO_SERVICO = [4, 4, 3, 3, 3, 2, 2, 1.5, 1.5, 1, 1, 1]

# serviços que fazem sentido por espécie
SERVICOS_POR_ESPECIE = {
    "Cão": {s[0] for s in SERVICOS},
    "Gato": {s[0] for s in SERVICOS} - {"Banho Grande Porte", "Day Care"},
    "Coelho": {"Consulta Veterinária", "Corte de Unhas", "Vermifugação"},
    "Pássaro": {"Consulta Veterinária", "Corte de Unhas"},
    "Hamster": {"Consulta Veterinária"},
}

ESPECIES = [  # (nome, peso, raças)
    ("Cão", 0.60, ["SRD (Vira-lata)", "Shih Tzu", "Poodle", "Golden Retriever", "Labrador",
                    "Bulldog Francês", "Yorkshire", "Pinscher", "Spitz Alemão", "Dachshund",
                    "Lhasa Apso", "Border Collie"]),
    ("Gato", 0.30, ["SRD (Vira-lata)", "Siamês", "Persa", "Maine Coon", "Angorá", "Ragdoll"]),
    ("Coelho", 0.04, ["Mini Lop", "Anão", "Rex"]),
    ("Pássaro", 0.04, ["Calopsita", "Periquito", "Canário"]),
    ("Hamster", 0.02, ["Sírio", "Anão Russo"]),
]

NOMES_PET = [
    "Thor", "Mel", "Luna", "Bob", "Nina", "Max", "Mia", "Toby", "Lola", "Simba", "Maya", "Bidu",
    "Pipoca", "Amora", "Fred", "Princesa", "Zeca", "Pandora", "Branco", "Cacau", "Billy", "Safira",
    "Hulk", "Estrela", "Duque", "Bella", "Floquinho", "Tigrão", "Gaia", "Spike", "Cleo", "Rex",
    "Nana", "Juca", "Lili", "Belinha", "Chico", "Pituca", "Zoe", "Bartolomeu",
]

BAIRROS = [
    "Mooca", "Tatuapé", "Vila Mariana", "Pinheiros", "Moema", "Santana", "Ipiranga", "Butantã",
    "Lapa", "Penha", "Itaim Bibi", "Saúde", "Jabaquara", "Vila Madalena", "Perdizes",
]

FORMAS_PAGAMENTO = ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"]
PESO_PAGAMENTO = [0.38, 0.32, 0.20, 0.10]

STATUS = ["Pago", "Pendente", "Cancelado"]
PESO_STATUS = [0.85, 0.08, 0.07]

# sazonalidade: dezembro e novembro vendem mais, fevereiro menos
PESO_MES = {12: 1.4, 11: 1.2, 1: 0.9, 2: 0.8}


def sortear_data_venda(data_cadastro: date) -> date:
    """Sorteia uma data na janela de 12 meses, nunca antes do cadastro do cliente."""
    inicio = max(data_cadastro, INICIO_JANELA)
    dias = (HOJE - inicio).days
    while True:
        d = inicio + timedelta(days=random.randint(0, dias))
        if random.random() < PESO_MES.get(d.month, 1.0) / 1.4:
            return d


def gerar_dados() -> dict:
    """Gera todas as tabelas em memória (listas de dicts, com IDs 1..N na ordem de inserção)."""
    categorias = [{"CategoriaID": i, "Nome": nome} for i, nome in enumerate(CATEGORIAS, start=1)]

    produtos = []
    for cat_id, categoria in enumerate(CATEGORIAS, start=1):
        for nome, preco in PRODUTOS[categoria]:
            produtos.append({
                "ProdutoID": len(produtos) + 1, "Nome": nome, "CategoriaID": cat_id,
                "Preco": preco, "Estoque": random.randint(0, 120),
            })

    servicos = [{"ServicoID": i, "Nome": n, "Preco": p} for i, (n, p) in enumerate(SERVICOS, start=1)]

    clientes, pets = [], []
    for cid in range(1, N_CLIENTES + 1):
        clientes.append({
            "ClienteID": cid,
            "Nome": f"{fake.first_name()} {fake.last_name()}",
            "Email": fake.unique.email(),
            "Bairro": random.choice(BAIRROS),
            "Cidade": "São Paulo",
            "DataCadastro": HOJE - timedelta(days=random.randint(30, 730)),
        })
        for _ in range(random.choices([1, 2, 3], [0.65, 0.28, 0.07])[0]):
            especie, _, racas = random.choices(ESPECIES, weights=[e[1] for e in ESPECIES])[0]
            pets.append({
                "PetID": len(pets) + 1, "ClienteID": cid, "Nome": random.choice(NOMES_PET),
                "Especie": especie, "Raca": random.choice(racas),
                "DataNascimento": HOJE - timedelta(days=random.randint(60, 14 * 365)),
            })

    pets_por_cliente = {}
    for p in pets:
        pets_por_cliente.setdefault(p["ClienteID"], []).append(p)

    # alguns clientes compram muito mais que outros -> clientes recorrentes
    peso_cliente = random.choices([1, 2, 3, 5], [0.5, 0.25, 0.15, 0.10], k=N_CLIENTES)
    prod_por_cat = {c["CategoriaID"]: [p for p in produtos if p["CategoriaID"] == c["CategoriaID"]]
                    for c in categorias}

    vendas, itens = [], []
    for vid in range(1, N_VENDAS + 1):
        cliente = random.choices(clientes, weights=peso_cliente)[0]
        vendas.append({
            "VendaID": vid, "ClienteID": cliente["ClienteID"],
            "DataVenda": sortear_data_venda(cliente["DataCadastro"]),
            "FormaPagamento": random.choices(FORMAS_PAGAMENTO, PESO_PAGAMENTO)[0],
            "Status": random.choices(STATUS, PESO_STATUS)[0],
        })

        for _ in range(random.choices([1, 2, 3, 4], [0.40, 0.30, 0.20, 0.10])[0]):
            desconto = random.choice([1, 1, 1, 0.95, 0.90])
            if random.random() < 0.62:  # item de produto
                cat = random.choices(categorias, weights=PESO_CATEGORIA)[0]
                prod = random.choice(prod_por_cat[cat["CategoriaID"]])
                itens.append({
                    "VendaID": vid, "ProdutoID": prod["ProdutoID"], "ServicoID": None, "PetID": None,
                    "Quantidade": random.choices([1, 2, 3], [0.70, 0.20, 0.10])[0],
                    "PrecoUnitario": round(prod["Preco"] * desconto, 2),
                })
            else:  # item de serviço, sempre para um pet do cliente
                pet = random.choice(pets_por_cliente[cliente["ClienteID"]])
                permitidos = [(s, w) for s, w in zip(servicos, PESO_SERVICO)
                              if s["Nome"] in SERVICOS_POR_ESPECIE[pet["Especie"]]]
                serv = random.choices([s for s, _ in permitidos], weights=[w for _, w in permitidos])[0]
                qtd = random.randint(1, 4) if serv["Nome"].startswith("Hotel") else 1
                itens.append({
                    "VendaID": vid, "ProdutoID": None, "ServicoID": serv["ServicoID"],
                    "PetID": pet["PetID"], "Quantidade": qtd,
                    "PrecoUnitario": round(serv["Preco"] * desconto, 2),
                })

    for i, item in enumerate(itens, start=1):
        item["ItemID"] = i

    return {
        "Categorias": categorias, "Produtos": produtos, "Servicos": servicos, "Clientes": clientes,
        "Pets": pets, "Vendas": vendas, "ItensVenda": itens,
    }


# ---------------------------------------------------------------- escrita do .sql
def lit(valor) -> str:
    """Formata um valor Python como literal T-SQL."""
    if valor is None:
        return "NULL"
    if isinstance(valor, str):
        return "N'" + valor.replace("'", "''") + "'"
    if isinstance(valor, date):
        return f"'{valor.isoformat()}'"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def blocos_insert(tabela: str, colunas: list, linhas: list, tamanho: int = 500) -> list:
    """O SQL Server aceita no máximo 1000 linhas por INSERT ... VALUES, então quebramos em blocos."""
    blocos = []
    for i in range(0, len(linhas), tamanho):
        valores = ",\n".join(
            "(" + ", ".join(lit(l[c]) for c in colunas) + ")" for l in linhas[i:i + tamanho]
        )
        blocos.append(f"INSERT INTO dbo.{tabela} ({', '.join(colunas)}) VALUES\n{valores};\nGO\n")
    return blocos


def gerar_script(dados: dict) -> str:
    partes = [f"USE {NOME_BANCO};", "GO", ""]
    colunas = {
        "Categorias": ["Nome"],
        "Produtos": ["Nome", "CategoriaID", "Preco", "Estoque"],
        "Servicos": ["Nome", "Preco"],
        "Clientes": ["Nome", "Email", "Bairro", "Cidade", "DataCadastro"],
        "Pets": ["ClienteID", "Nome", "Especie", "Raca", "DataNascimento"],
        "Vendas": ["ClienteID", "DataVenda", "FormaPagamento", "Status"],
        "ItensVenda": ["VendaID", "ProdutoID", "ServicoID", "PetID", "Quantidade", "PrecoUnitario"],
    }
    for tabela, cols in colunas.items():
        partes.append(f"-- {tabela}")
        partes.extend(blocos_insert(tabela, cols, dados[tabela]))
    return "\n".join(partes)


if __name__ == "__main__":
    dados = gerar_dados()
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql", "02_inserir_dados.sql")
    # utf-8 com BOM: garante que o SSMS leia os acentos corretamente
    with open(destino, "w", encoding="utf-8-sig") as f:
        f.write(gerar_script(dados))
    print(f"Script gerado em: {os.path.normpath(destino)}")
    for tabela, linhas in dados.items():
        print(f"  {tabela}: {len(linhas)} linhas")
