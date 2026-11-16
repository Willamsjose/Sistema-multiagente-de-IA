"""
projectsolution.py
Sistema Multiagente Completo para Gestão de Inventário, Cotações e Vendas
Beaver's Choice Paper Company
Autor: Especialista em IA / Consultor de Sistemas Multiagentes
"""

import os
import sqlite3
import csv
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ==========================================
# CONFIGURAÇÃO DO CLIENTE OPENAI (VOCAREUM)
# ==========================================
client = OpenAI()

DB_NAME = "beavers_choice.db"

# ==========================================
# FUNÇÕES DE BANCO DE DADOS E AUXILIARES
# ==========================================
def init_db():
    """Inicializa o banco de dados SQLite com tabelas de inventário, cotações, transações e finanças."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_type TEXT UNIQUE,
            stock_level INTEGER,
            unit_price REAL,
            supplier_lead_time_days INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            paper_type TEXT,
            quantity INTEGER,
            quoted_price REAL,
            status TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            paper_type TEXT,
            quantity INTEGER,
            total_amount REAL,
            delivery_date TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cash_balance REAL
        )
    ''')

    # Populando dados iniciais de exemplo, se vazio
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        initial_inventory = [
            ("A4 Copy Paper", 5000, 10.0, 3),
            ("Cardstock Glossy", 1200, 25.0, 5),
            ("Recycled Kraft", 3000, 15.0, 4),
            ("Newsprint", 800, 8.0, 7)
        ]
        cursor.executemany("INSERT INTO inventory (paper_type, stock_level, unit_price, supplier_lead_time_days) VALUES (?, ?, ?, ?)", initial_inventory)
        
        cursor.execute("INSERT INTO company_finances (cash_balance) VALUES (50000.0)")
        
        initial_quotes = [
            ("Acme Corp", "A4 Copy Paper", 500, 4800.0, "Accepted", "2026-10-01"),
            ("PrintShop Ltda", "Cardstock Glossy", 200, 4800.0, "Accepted", "2026-10-05")
        ]
        cursor.executemany("INSERT INTO quotes (customer_name, paper_type, quantity, quoted_price, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)", initial_quotes)

    conn.commit()
    conn.close()

# --- Funções obrigatórias e utilitárias ---

def getstocklevel(paper_type: str) -> int:
    """Retorna o nível atual de estoque para um determinado tipo de papel."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT stock_level FROM inventory WHERE paper_type = ?", (paper_type,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def getallinventory() -> dict:
    """Retorna o inventário completo da empresa."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT paper_type, stock_level, unit_price, supplier_lead_time_days FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: {"stock": row[1], "price": row[2], "lead_time": row[3]} for row in rows}

def getsupplierdeliverydate(paper_type: str, quantity: int) -> str:
    """Calcula a data estimada de entrega baseada no lead time do fornecedor."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT supplier_lead_time_days, stock_level FROM inventory WHERE paper_type = ?", (paper_type,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Indisponível"
    lead_time, stock = row
    days_to_add = lead_time if quantity > stock else 1
    return f"Estimado em {days_to_add} dias úteis"

def searchquotehistory(customer_name: str, paper_type: str) -> list:
    """Busca o histórico de cotações para um cliente e tipo de papel específicos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, quoted_price, status, timestamp FROM quotes WHERE customer_name = ? AND paper_type = ?", (customer_name, paper_type))
    rows = cursor.fetchall()
    conn.close()
    return [{"quantity": r[0], "price": r[1], "status": r[2], "date": r[3]} for r in rows]

def createtransaction(customer_name: str, paper_type: str, quantity: int, total_amount: float, delivery_date: str) -> bool:
    """Cria uma transação de venda, atualiza o estoque e o saldo em caixa."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock_level FROM inventory WHERE paper_type = ?", (paper_type,))
    row = cursor.fetchone()
    if not row or row[0] < quantity:
        conn.close()
        return False
    
    new_stock = row[0] - quantity
    cursor.execute("UPDATE inventory SET stock_level = ? WHERE paper_type = ?", (new_stock, paper_type))
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (customer_name, paper_type, quantity, total_amount, delivery_date, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                   (customer_name, paper_type, quantity, total_amount, delivery_date, timestamp))
    
    cursor.execute("SELECT cash_balance FROM company_finances")
    current_cash = cursor.fetchone()[0]
    new_cash = current_cash + total_amount
    cursor.execute("UPDATE company_finances SET cash_balance = ?", (new_cash,))
    
    conn.commit()
    conn.close()
    return True

def getcashbalance() -> float:
    """Retorna o saldo de caixa atual da empresa."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT cash_balance FROM company_finances")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

def generatefinancialreport() -> str:
    """Gera um relatório financeiro e de inventário global."""
    inventory = getallinventory()
    cash = getcashbalance()
    report = f"--- RELATÓRIO FINANCEIRO E DE INVENTÁRIO ---\n"
    report += f"Saldo em Caixa Atual: R$ {cash:.2f}\n"
    report += f"Inventário Disponível:\n"
    for paper, details in inventory.items():
        report += f" - {paper}: {details['stock']} unidades (Preço Unitário: R$ {details['price']:.2f}, Lead Time: {details['lead_time']} dias)\n"
    return report

def save_quote_to_db(customer_name: str, paper_type: str, quantity: int, quoted_price: float, status: str) -> int:
    """Salva permanentemente uma cotação gerada no banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO quotes (customer_name, paper_type, quantity, quoted_price, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (customer_name, paper_type, quantity, quoted_price, status, timestamp)
    )
    conn.commit()
    quote_id = cursor.lastrowid
    conn.close()
    return quote_id

def restock_item(paper_type: str, quantity_to_add: int) -> dict:
    """Simula a compra de suprimentos de papel junto ao fornecedor, atualizando estoque e caixa."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT unit_price, stock_level FROM inventory WHERE paper_type = ?", (paper_type,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "reason": "Tipo de papel não encontrado."}
        
    unit_price, current_stock = row
    wholesale_cost = (unit_price * 0.6) * quantity_to_add
    
    cursor.execute("SELECT cash_balance FROM company_finances")
    current_cash = cursor.fetchone()[0]
    
    if current_cash < wholesale_cost:
        conn.close()
        return {"success": False, "reason": "Caixa insuficiente para o reabastecimento."}
        
    new_stock = current_stock + quantity_to_add
    new_cash = current_cash - wholesale_cost
    
    cursor.execute("UPDATE inventory SET stock_level = ? WHERE paper_type = ?", (new_stock, paper_type))
    cursor.execute("UPDATE company_finances SET cash_balance = ?", (new_cash,))
    
    conn.commit()
    conn.close()
    return {"success": True, "paper_type": paper_type, "added": quantity_to_add, "total_cost": wholesale_cost}

def check_and_auto_replenish(threshold: int = 1000, restock_amount: int = 2000) -> list:
    """Verifica estoques críticos e executa reposição automática."""
    inventory = getallinventory()
    logs = []
    for paper, details in inventory.items():
        if details["stock"] < threshold:
            print(f"\n[InventoryAgent] ⚠️ Estoque de '{paper}' crítico ({details['stock']} un.). Reabastecendo...")
            res = restock_item(paper, restock_amount)
            logs.append(res)
            if res["success"]:
                print(f"[InventoryAgent] ✅ +{restock_amount} un. de '{paper}' adicionadas. Custo: R$ {res['total_cost']:.2f}")
    return logs

def export_data_to_csv():
    """Exporta cotações e transações para arquivos CSV."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, customer_name, paper_type, quantity, quoted_price, status, timestamp FROM quotes")
    quotes_rows = cursor.fetchall()
    with open("exported_quotes.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Cliente", "Tipo de Papel", "Quantidade", "Preço Cotado (R$)", "Status", "Timestamp"])
        writer.writerows(quotes_rows)
        
    cursor.execute("SELECT id, customer_name, paper_type, quantity, total_amount, delivery_date, timestamp FROM transactions")
    trans_rows = cursor.fetchall()
    with open("exported_transactions.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Cliente", "Tipo de Papel", "Quantidade", "Valor Total (R$)", "Data de Entrega", "Timestamp"])
        writer.writerows(trans_rows)
        
    conn.close()
    print("\n" + "="*50)
    print(" ✅ EXPORTAÇÃO CONCLUÍDA: 'exported_quotes.csv' e 'exported_transactions.csv'")
    print("="*50 + "\n")

def analyze_financial_performance():
    """Gera análise executiva de desempenho financeiro utilizando IA."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash_balance FROM company_finances")
    current_cash = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM transactions")
    trans_count, total_revenue = cursor.fetchone()
    trans_count, total_revenue = trans_count or 0, total_revenue or 0.0
    
    cursor.execute("SELECT COUNT(*) FROM quotes")
    total_quotes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM quotes WHERE status = 'Accepted'")
    accepted_quotes = cursor.fetchone()[0] or 0
    conversion_rate = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0.0
    
    conn.close()
    
    summary = f"""
    - Caixa Atual: R$ {current_cash:.2f}
    - Faturamento: R$ {total_revenue:.2f}
    - Vendas Concluídas: {trans_count}
    - Cotações Totais: {total_quotes}
    - Taxa de Conversão: {conversion_rate:.1f}%
    """
    
    print("\n" + "="*65)
    print(" 📊 GERANDO RELATÓRIO ANALÍTICO COM IA (GPT-4o)...")
    print("="*65)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um consultor financeiro corporativo especialista em suprimentos."},
                {"role": "user", "content": f"Elabore um relatório executivo conciso baseado nestas métricas:\n{summary}"}
            ],
            temperature=0.7
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erro ao acionar IA: {e}\nResumo: {summary}")
    print("="*65 + "\n")


# ==========================================
# ARQUITETURA DOS AGENTES MULTIAGENTES
# ==========================================
class InventoryAgent:
    def check_inventory(self, paper_type: str, quantity: int) -> dict:
        check_and_auto_replenish(threshold=1000, restock_amount=2000)
        stock = getstocklevel(paper_type)
        all_inv = getallinventory()
        delivery = getsupplierdeliverydate(paper_type, quantity)
        return {"sufficient": stock >= quantity, "current_stock": stock, "delivery_estimate": delivery, "catalog": all_inv}

class QuotationAgent:
    def generate_quote(self, customer_name: str, paper_type: str, quantity: int, status: str = "Pending") -> dict:
        history = searchquotehistory(customer_name, paper_type)
        all_inv = getallinventory()
        base_price = all_inv.get(paper_type, {}).get("price", 10.0)
        
        discount = 0.15 if quantity >= 1000 else (0.10 if quantity >= 500 else (0.05 if quantity >= 200 else 0.0))
        unit_price_discounted = base_price * (1 - discount)
        total_price = unit_price_discounted * quantity
        
        save_quote_to_db(customer_name, paper_type, quantity, total_price, status)
        return {"unit_price": unit_price_discounted, "total_price": total_price, "discount_applied": f"{discount * 100}%", "history_found": len(history) > 0}

class SalesAndFinanceAgent:
    def process_sale(self, customer_name: str, paper_type: str, quantity: int, total_amount: float, delivery_date: str) -> bool:
        return createtransaction(customer_name, paper_type, quantity, total_amount, delivery_date)

class OrchestratorAgent:
    def __init__(self):
        self.inventory_agent = InventoryAgent()
        self.quotation_agent = QuotationAgent()
        self.sales_agent = SalesAndFinanceAgent()

    def handle_request(self, customer_name: str, paper_type: str, requested_quantity: int, max_budget: float = None) -> dict:
        print(f"\n[Orchestrator] Processando pedido de '{customer_name}' ({requested_quantity}x {paper_type})...")
        
        inv_status = self.inventory_agent.check_inventory(paper_type, requested_quantity)
        if not inv_status["sufficient"]:
            reason = f"Estoque insuficiente. Disponível: {inv_status['current_stock']}, Solicitado: {requested_quantity}."
            print(f"[Orchestrator] Pedido REJEITADO: {reason}")
            save_quote_to_db(customer_name, paper_type, requested_quantity, 0.0, "Rejected")
            return {"status": "Rejected", "reason": reason}
        
        quote = self.quotation_agent.generate_quote(customer_name, paper_type, requested_quantity, status="Accepted")
        
        if max_budget and quote["total_price"] > max_budget:
            reason = f"Cotação (R$ {quote['total_price']:.2f}) excede o orçamento (R$ {max_budget:.2f})."
            print(f"[Orchestrator] Pedido REJEITADO: {reason}")
            return {"status": "Rejected", "reason": reason}
            
        delivery_date = inv_status["delivery_estimate"]
        success = self.sales_agent.process_sale(customer_name, paper_type, requested_quantity, quote["total_price"], delivery_date)
        
        if success:
            print(f"[Orchestrator] Pedido APROVADO! Valor: R$ {quote['total_price']:.2f}")
            return {"status": "Accepted", "total_price": quote["total_price"], "delivery": delivery_date}
        else:
            return {"status": "Rejected", "reason": "Erro ao gravar transação no banco de dados."}

# ==========================================
# MODOS DE EXECUÇÃO (TESTES / INTERATIVO)
# ==========================================
def run_evaluation():
    init_db()
    orchestrator = OrchestratorAgent()
    
    sample_requests = [
        {"customer": "Alpha Pubs", "paper": "A4 Copy Paper", "qty": 600, "budget": 6000.0},
        {"customer": "Beta Books", "paper": "Cardstock Glossy", "qty": 1500, "budget": 40000.0},
        {"customer": "Gamma Corp", "paper": "Newsprint", "qty": 200, "budget": 2000.0},
        {"customer": "Delta Stationery", "paper": "Recycled Kraft", "qty": 5000, "budget": 40000.0}
    ]
    
    results = []
    for req in sample_requests:
        res = orchestrator.handle_request(req["customer"], req["paper"], req["qty"], req["budget"])
        results.append({
            "customer": req["customer"], "paper": req["paper"], "quantity": req["qty"],
            "status": res["status"], "detail": res.get("total_price", res.get("reason"))
        })
        
    with open("testresults.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer", "paper", "quantity", "status", "detail"])
        writer.writeheader()
        writer.writerows(results)
        
    print("\n[Avaliação Concluída] Arquivo 'testresults.csv' gerado com sucesso!")
    print(generatefinancialreport())

def run_interactive_cli():
    init_db()
    orchestrator = OrchestratorAgent()
    
    print("\n" + "="*65)
    print(" 🖨️  SISTEMA MULTIAGENTE - BEAVER'S CHOICE PAPER COMPANY")
    print("="*65)
    
    while True:
        print("\n--- MENU PRINCIPAL ---")
        print(" [1] Realizar nova cotação / pedido interativo")
        print(" [2] Exibir relatório financeiro e inventário global")
        print(" [3] Exportar histórico para CSV (Cotações e Transações)")
        print(" [4] Executar Análise de Desempenho com IA 📊")
        print(" [5] Verificar Estoque e Forçar Reabastecimento Automático 📦")
        print(" [6] Sair do sistema")
        
        opcao = input("\nEscolha uma opção (1-6): ").strip()
        
        if opcao == "6":
            print("\nEncerrando o sistema. Até logo!")
            break
        elif opcao == "2":
            print("\n" + generatefinancialreport() + "\n")
            continue
        elif opcao == "3":
            export_data_to_csv()
            continue
        elif opcao == "4":
            analyze_financial_performance()
            continue
        elif opcao == "5":
            print("\n--- VARREDURA DE REABASTECIMENTO ---")
            check_and_auto_replenish(threshold=1500, restock_amount=2000)
            print("-" * 40 + "\n")
            continue
        elif opcao != "1":
            print("⚠️ Opção inválida. Digite de 1 a 6.\n")
            continue
            
        customer = input("\n👤 Nome do Cliente: ").strip()
        if not customer:
            print("⚠️ O nome não pode estar vazio.\n")
            continue
            
        print("\n📦 Catálogo Atual:")
        inventory = getallinventory()
        for paper, details in inventory.items():
            print(f"   • {paper} | Estoque: {details['stock']} un. | Preço Base: R$ {details['price']:.2f} | Lead Time: {details['lead_time']} dias")
        
        paper_type = input("\n📄 Tipo de papel desejado: ").strip()
        if paper_type not in inventory:
            print(f"⚠️ '{paper_type}' não encontrado no catálogo.\n")
            continue
            
        try:
            qty = int(input("🔢 Quantidade desejada: ").strip())
            if qty <= 0: raise ValueError
        except ValueError:
            print("⚠️ Digite um número inteiro positivo válido.\n")
            continue
            
        budget_input = input("💰 Orçamento máximo (opcional, Enter para ignorar): ").strip()
        budget = float(budget_input) if budget_input else None
        
        print("\n" + "-"*40)
        result = orchestrator.handle_request(customer, paper_type, qty, budget)
        print("-" * 40)
        
        if result["status"] == "Accepted":
            print(f"🎉 Pedido APROVADO! Total: R$ {result['total_price']:.2f} | Entrega: {result['delivery']}\n")
        else:
            print(f"❌ Pedido REJEITADO. Motivo: {result['reason']}\n")

if __name__ == "__main__":
    print("Selecione o modo de execução:")
    print(" [1] Executar Testes Automáticos (Gera 'testresults.csv')")
    print(" [2] Iniciar Menu Interativo no Terminal")
    
    escolha = input("\nDigite sua opção (1 ou 2): ").strip()
    if escolha == "2":
        run_interactive_cli()
    else:
        run_evaluation()
