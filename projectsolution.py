"""
projectsolution.py
Sistema Multiagente Refatorado com smolagents para Gestão de Inventário, Cotações e Vendas
Beaver's Choice Paper Company
"""

import os
import sqlite3
import csv
from datetime import datetime
from dotenv import load_dotenv
from smolagents import ToolCallingAgent, OpenAIServerModel, tool

load_dotenv()

# ==========================================
# CONFIGURAÇÃO DO MODELO (SMOLAGENTS + OPENAI)
# ==========================================
# Suporta tanto a chave padrão da OpenAI quanto a Vocareum (caso OPENAI_BASE_URL esteja no .env)
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY")
)

DBNAME = "beaverschoice.db"

# ==========================================
# INICIALIZAÇÃO DO BANCO DE DADOS SQLITE
# ==========================================
def initdb():
    """Inicializa o banco de dados SQLite com tabelas de inventário, cotações, transações e finanças."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            papertype TEXT UNIQUE,
            stocklevel INTEGER,
            unitprice REAL,
            supplierleadtimedays INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customername TEXT,
            papertype TEXT,
            quantity INTEGER,
            quotedprice REAL,
            status TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customername TEXT,
            papertype TEXT,
            quantity INTEGER,
            totalamount REAL,
            deliverydate TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companyfinances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cashbalance REAL
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        initialinventory = [
            ("A4 Copy Paper", 5000, 10.0, 3),
            ("Cardstock Glossy", 1200, 25.0, 5),
            ("Recycled Kraft", 3000, 15.0, 4),
            ("Newsprint", 800, 8.0, 7)
        ]
        cursor.executemany(
            "INSERT INTO inventory (papertype, stocklevel, unitprice, supplierleadtimedays) VALUES (?, ?, ?, ?)",
            initialinventory
        )
        cursor.execute("INSERT INTO companyfinances (cashbalance) VALUES (50000.0)")
        initialquotes = [
            ("Acme Corp", "A4 Copy Paper", 500, 4800.0, "Accepted", "2026-10-01"),
            ("PrintShop Ltda", "Cardstock Glossy", 200, 4800.0, "Accepted", "2026-10-05")
        ]
        cursor.executemany(
            "INSERT INTO quotes (customername, papertype, quantity, quotedprice, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            initialquotes
        )

    conn.commit()
    conn.close()

# ==========================================
# FERRAMENTAS REGISTRADAS VIA @tool (SMOLAGENTS)
# ==========================================

@tool
def getstocklevel(papertype: str) -> int:
    """
    Retorna o nível atual de estoque para um determinado tipo de papel.

    Args:
        papertype: O nome exato do tipo de papel no catálogo (ex: 'A4 Copy Paper', 'Cardstock Glossy', 'Recycled Kraft', 'Newsprint').
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT stocklevel FROM inventory WHERE papertype = ?", (papertype,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

@tool
def getallinventory() -> str:
    """
    Retorna o inventário completo da empresa contendo estoque, preço unitário e prazo de entrega do fornecedor.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT papertype, stocklevel, unitprice, supplierleadtimedays FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    inv = {row[0]: {"stock": row[1], "price": row[2], "leadtime": row[3]} for row in rows}
    return str(inv)

@tool
def getsupplierdeliverydate(papertype: str, quantity: int) -> str:
    """
    Calcula o prazo estimado de entrega baseado no lead time do fornecedor e estoque atual.

    Args:
        papertype: O nome exato do tipo de papel.
        quantity: A quantidade solicitada pelo cliente.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT supplierleadtimedays, stocklevel FROM inventory WHERE papertype = ?", (papertype,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Indisponível"
    leadtime, stock = row
    daystoadd = leadtime if quantity > stock else 1
    return f"Estimado em {daystoadd} dias úteis"

@tool
def restockitem(papertype: str, quantitytoadd: int) -> str:
    """
    Realiza a compra de reposição de suprimentos junto ao fornecedor, atualizando o estoque e deduzindo o custo do caixa.

    Args:
        papertype: O nome exato do tipo de papel a ser reabastecido.
        quantitytoadd: Quantidade de unidades a adicionar ao estoque.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT unitprice, stocklevel FROM inventory WHERE papertype = ?", (papertype,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Falha: Tipo de papel não encontrado."
    unitprice, currentstock = row
    wholesalecost = (unitprice * 0.6) * quantitytoadd
    cursor.execute("SELECT cashbalance FROM companyfinances")
    currentcash = cursor.fetchone()[0]
    if currentcash < wholesalecost:
        conn.close()
        return "Falha: Caixa insuficiente para o reabastecimento."
    newstock = currentstock + quantitytoadd
    newcash = currentcash - wholesalecost
    cursor.execute("UPDATE inventory SET stocklevel = ? WHERE papertype = ?", (newstock, papertype))
    cursor.execute("UPDATE companyfinances SET cashbalance = ?", (newcash,))
    conn.commit()
    conn.close()
    return f"Sucesso: +{quantitytoadd} unidades de {papertype} adicionadas. Novo estoque: {newstock}. Custo: R$ {wholesalecost:.2f}"

@tool
def searchquotehistory(customername: str, papertype: str) -> str:
    """
    Busca o histórico de cotações anteriores para um cliente e tipo de papel específicos.

    Args:
        customername: Nome do cliente.
        papertype: Nome do tipo de papel.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT quantity, quotedprice, status, timestamp FROM quotes WHERE customername = ? AND papertype = ?",
        (customername, papertype)
    )
    rows = cursor.fetchall()
    conn.close()
    history = [{"quantity": r[0], "price": r[1], "status": r[2], "date": r[3]} for r in rows]
    return str(history) if history else "Nenhum histórico encontrado para este cliente/item."

@tool
def savequotetodb(customername: str, papertype: str, quantity: int, quotedprice: float, status: str) -> str:
    """
    Registra uma cotação calculada (aceita ou rejeitada) no banco de dados SQLite.

    Args:
        customername: Nome do cliente.
        papertype: Nome do tipo de papel.
        quantity: Quantidade cotada.
        quotedprice: Valor total cotado em reais.
        status: Status da cotação ('Accepted' ou 'Rejected').
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO quotes (customername, papertype, quantity, quotedprice, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (customername, papertype, quantity, quotedprice, status, timestamp)
    )
    conn.commit()
    quoteid = cursor.lastrowid
    conn.close()
    return f"Cotação #{quoteid} registrada com status '{status}'."

@tool
def createtransaction(customername: str, papertype: str, quantity: int, totalamount: float, deliverydate: str) -> str:
    """
    Finaliza uma transação de venda aprovada: deduz o estoque, registra a venda e adiciona o valor ao saldo em caixa.

    Args:
        customername: Nome do cliente.
        papertype: Tipo de papel vendido.
        quantity: Quantidade vendida.
        totalamount: Valor total da venda a ser creditado no caixa.
        deliverydate: Prazo de entrega estimado.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT stocklevel FROM inventory WHERE papertype = ?", (papertype,))
    row = cursor.fetchone()
    if not row or row[0] < quantity:
        conn.close()
        return "Erro: Estoque insuficiente no momento da gravação da transação."
    
    newstock = row[0] - quantity
    cursor.execute("UPDATE inventory SET stocklevel = ? WHERE papertype = ?", (newstock, papertype))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO transactions (customername, papertype, quantity, totalamount, deliverydate, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (customername, papertype, quantity, totalamount, deliverydate, timestamp)
    )
    cursor.execute("SELECT cashbalance FROM companyfinances")
    currentcash = cursor.fetchone()[0]
    newcash = currentcash + totalamount
    cursor.execute("UPDATE companyfinances SET cashbalance = ?", (newcash,))
    conn.commit()
    conn.close()
    return f"Transação concluída com sucesso! Novo saldo em caixa: R$ {newcash:.2f}."

@tool
def getcashbalance() -> float:
    """
    Retorna o saldo de caixa atual da empresa Beaver's Choice Paper Company.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT cashbalance FROM companyfinances")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

@tool
def generatefinancialreport() -> str:
    """
    Gera um relatório financeiro e de inventário global atualizado da empresa.
    """
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT papertype, stocklevel, unitprice, supplierleadtimedays FROM inventory")
    rows = cursor.fetchall()
    cursor.execute("SELECT cashbalance FROM companyfinances")
    cash = cursor.fetchone()[0]
    conn.close()

    report = "--- RELATÓRIO FINANCEIRO E DE INVENTÁRIO ---\n"
    report += f"Saldo em Caixa Atual: R$ {cash:.2f}\n"
    report += "Inventário Disponível:\n"
    for r in rows:
        report += f" - {r[0]}: {r[1]} unidades (Preço Unitário: R$ {r[2]:.2f}, Lead Time: {r[3]} dias)\n"
    return report

# ==========================================
# ARQUITETURA MULTIAGENTE (SMOLAGENTS)
# ==========================================

# 1. Agente Trabalhador de Inventário
inventory_agent = ToolCallingAgent(
    tools=[getstocklevel, getallinventory, getsupplierdeliverydate, restockitem],
    model=model,
    name="inventory_agent",
    description="Especialista em inventário. Verifica níveis de estoque, catálogo de produtos, prazos de entrega de fornecedores e realiza reposição quando necessário.",
    instructions=(
        "Você é o Agente de Inventário da Beaver's Choice Paper Company. "
        "Sempre verifique o estoque atual usando getstocklevel ou getallinventory e o prazo usando getsupplierdeliverydate. "
        "Se um item existente no catálogo estiver com estoque abaixo de 1000 unidades (mas o pedido atual não exceder absurdamente a capacidade física), avalie se deve acionar restockitem. "
        "Informe claramente se há estoque suficiente para atender a quantidade solicitada pelo cliente."
    )
)

# 2. Agente Trabalhador de Cotações
quotation_agent = ToolCallingAgent(
    tools=[searchquotehistory, getallinventory, savequotetodb],
    model=model,
    name="quotation_agent",
    description="Especialista em precificação e cotações. Consulta histórico de clientes, aplica descontos por volume e registra cotações no banco.",
    instructions=(
        "Você é o Agente de Cotações da Beaver's Choice Paper Company. "
        "Consulte o preço base via getallinventory e o histórico via searchquotehistory. "
        "Aplique rigorosamente a política de descontos por volume: "
        "0% para < 200 unidades; 5% para >= 200 unidades; 10% para >= 500 unidades; 15% para >= 1000 unidades. "
        "Calcule o valor unitário com desconto e o valor total. Registre a cotação usando savequotetodb."
    )
)

# 3. Agente Trabalhador de Vendas e Finanças
sales_agent = ToolCallingAgent(
    tools=[createtransaction, getcashbalance, generatefinancialreport],
    model=model,
    name="sales_agent",
    description="Especialista em fechamento de vendas e finanças. Processa transações aprovadas no banco de dados, atualiza o saldo em caixa e gera relatórios financeiros.",
    instructions=(
        "Você é o Agente de Vendas e Finanças. "
        "Quando um pedido tiver estoque confirmado e cotação aprovada dentro do orçamento, execute createtransaction para finalizar a venda e atualizar o caixa. "
        "Use getcashbalance ou generatefinancialreport para confirmar a saúde financeira após grandes transações."
    )
)

# 4. Agente Orquestrador Principal
orchestrator_agent = ToolCallingAgent(
    tools=[],
    managed_agents=[inventory_agent, quotation_agent, sales_agent],
    model=model,
    name="orchestrator_agent",
    description="Orquestrador principal que coordena o atendimento ao cliente delegando tarefas aos agentes especialistas.",
    instructions=(
        "Você é o Agente Orquestrador da Beaver's Choice Paper Company. Siga estritamente este fluxo de 3 etapas para cada pedido:\n"
        "1. Delegue ao 'inventory_agent' para verificar se o tipo de papel existe e se há estoque suficiente e prazo de entrega.\n"
        "   - Se NÃO houver estoque suficiente ou o item não existir, REJEITE o pedido imediatamente explicando o motivo claro ao cliente (não conclua a venda).\n"
        "2. Delegue ao 'quotation_agent' para calcular o preço total aplicando os descontos por volume e salvar a cotação.\n"
        "   - Se o cliente informou um orçamento máximo e o valor cotado exceder esse orçamento, REJEITE o pedido explicando o valor cotado vs. orçamento.\n"
        "3. Delegue ao 'sales_agent' para concluir a transação via createtransaction.\n"
        "Ao final, responda sempre iniciando com 'STATUS: Accepted' ou 'STATUS: Rejected' seguido da justificativa transparente para o cliente (sem expor detalhes internos sensíveis)."
    )
)

# ==========================================
# FUNÇÃO DE ORQUESTRAÇÃO E AVALIAÇÃO (Q5)
# ==========================================

def process_customer_request(customer_name: str, papertype: str, quantity: int, max_budget: float = None, raw_request: str = "") -> dict:
    """Envia a requisição estruturada ou em texto livre para o Agente Orquestrador smolagents."""
    budget_text = f"Orçamento máximo do cliente: R$ {max_budget:.2f}." if max_budget else "Sem limite de orçamento especificado."
    prompt = (
        f"Nova solicitação de cliente:\n"
        f"- Cliente: {customer_name}\n"
        f"- Tipo de Papel: {papertype}\n"
        f"- Quantidade: {quantity}\n"
        f"- {budget_text}\n"
        f"- Detalhes adicionais da requisição: {raw_request}\n\n"
        f"Processe este pedido seguindo o fluxo de verificação de inventário, cotação e fechamento de venda."
    )
    
    print(f"\n[Orchestrator] Delegando pedido de '{customer_name}' ({quantity}x {papertype})...")
    response_text = str(orchestrator_agent.run(prompt))
    
    status = "Accepted" if "STATUS: Accepted" in response_text else "Rejected"
    return {
        "status": status,
        "detail": response_text.replace("\n", " ").strip()
    }

def runevaluation():
    """
    Carrega o dataset oficial 'quoterequestssample.csv', executa todas as requisições
    através do sistema multiagente smolagents e salva os resultados em 'testresults.csv'.
    """
    initdb()
    input_file = "quoterequestssample.csv"
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"O arquivo '{input_file}' não foi encontrado no diretório atual. "
            "Certifique-se de colocar o 'quoterequestssample.csv' fornecido pela Udacity na raiz do projeto."
        )

    results = []
    initial_cash = getcashbalance()
    print(f"[Avaliação Iniciada] Saldo em caixa inicial: R$ {initial_cash:.2f}")

    with open(input_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # Mapeamento flexível para suportar as colunas padrão do dataset da Udacity
            customer = row.get("customer_name") or row.get("customer") or row.get("Customer") or f"Cliente_{idx}"
            paper = row.get("paper_type") or row.get("paper") or row.get("item") or row.get("Paper Type") or ""
            raw_qty = row.get("quantity") or row.get("qty") or row.get("Quantity") or "0"
            raw_budget = row.get("budget") or row.get("max_budget") or row.get("Budget") or ""
            raw_text = row.get("request") or row.get("query") or str(row)

            try:
                qty = int(float(raw_qty))
            except ValueError:
                qty = 0

            try:
                budget = float(raw_budget) if raw_budget.strip() else None
            except ValueError:
                budget = None

            cash_before = getcashbalance()
            res = process_customer_request(customer, paper, qty, budget, raw_text)
            cash_after = getcashbalance()

            results.append({
                "request_id": idx,
                "customer": customer,
                "paper_type": paper,
                "quantity": qty,
                "budget": budget if budget is not None else "N/A",
                "status": res["status"],
                "cash_before": f"{cash_before:.2f}",
                "cash_after": f"{cash_after:.2f}",
                "cash_changed": cash_after != cash_before,
                "explanation": res["detail"]
            })

    output_file = "testresults.csv"
    fieldnames = [
        "request_id", "customer", "paper_type", "quantity", "budget",
        "status", "cash_before", "cash_after", "cash_changed", "explanation"
    ]
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[Avaliação Concluída] Resultados salvos em '{output_file}'.")
    print(generatefinancialreport())

def runinteractivecli():
    """Interface interativa no terminal para testes manuais."""
    initdb()
    print("\n" + "=" * 65)
    print(" 🖨️  SISTEMA MULTIAGENTE (SMOLAGENTS) - BEAVER'S CHOICE")
    print("=" * 65)

    while True:
        print("\n--- MENU PRINCIPAL ---")
        print(" [1] Realizar nova cotação / pedido interativo")
        print(" [2] Exibir relatório financeiro e inventário global")
        print(" [3] Executar avaliação completa (quoterequestssample.csv -> testresults.csv)")
        print(" [4] Sair")

        opcao = input("\nEscolha uma opção (1-4): ").strip()

        if opcao == "4":
            break
        elif opcao == "2":
            print("\n" + generatefinancialreport())
        elif opcao == "3":
            runevaluation()
        elif opcao == "1":
            customer = input("\n👤 Nome do Cliente: ").strip()
            print("\n📦 Catálogo Atual:\n" + getallinventory())
            papertype = input("\n📄 Tipo de papel desejado: ").strip()
            qty = int(input("🔢 Quantidade desejada: ").strip())
            budget_in = input("💰 Orçamento máximo (Enter para ignorar): ").strip()
            budget = float(budget_in) if budget_in else None

            res = process_customer_request(customer, papertype, qty, budget)
            print(f"\nResultado: {res['status']}\nDetalhes: {res['detail']}\n")
        else:
            print("⚠️ Opção inválida.")

if __name__ == "__main__":
    print("Selecione o modo de execução:")
    print(" [1] Executar Avaliação Oficial (Lê 'quoterequestssample.csv' e gera 'testresults.csv')")
    print(" [2] Iniciar Menu Interativo no Terminal")
    escolha = input("\nDigite sua opção (1 ou 2): ").strip()
    if escolha == "2":
        runinteractivecli()
    else:
        runevaluation()
