import json
from escpos.printer import Network

# ---------------- BASE INTERFACE ----------------

class FiscalPrinter:
    def open_receipt(self):
        raise NotImplementedError

    def sell_item(self, description, qty, price, vat):
        raise NotImplementedError

    def payment(self, payment_type, amount):
        raise NotImplementedError

    def close_receipt(self):
        raise NotImplementedError

# ---------------- DADO RT30 (STUB) ----------------

class DadoRT30Printer(FiscalPrinter):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def open_receipt(self):
        print("[RT30] OPEN RECEIPT")

    def sell_item(self, description, qty, price, vat):
        print(f"[RT30] ITEM {qty}x {description} {price}€ VAT{vat}")

    def payment(self, payment_type, amount):
        print(f"[RT30] PAYMENT {payment_type} {amount}€")

    def close_receipt(self):
        print("[RT30] CLOSE RECEIPT")

# ---------------- COMANDA (ESC/POS) ----------------

SEPARATOR = "-" * 32 + "\n"

def print_comanda(cfg, order):
    p = Network(cfg["ip"], cfg["port"])

    p.set(align="center", bold=True, width=2, height=2)
    p.text("COMANDA\n")
    p.text(order["service"]["type"] + "\n")

    p.set(width=1, height=1)
    p.text(SEPARATOR)

    svc = order["service"]
    p.set(align="left", bold=True)

    if svc.get("tavolo"):
        p.text(f'Tavolo: {svc["tavolo"]}\n')
    else:
        p.text("Banco\n")

    p.text(f'Sala: {svc["sala"]}\n')
    p.text(f'Operatore: {svc["operatore"]}\n')
    p.text(f'Coperto: {svc["coperti"]}\n')

    p.text(SEPARATOR)
    p.set(bold=False)

    for l in order["lines"]:
        p.text(f'{l["qty"]} x {l["description"]}\n')
        p.text(f'   {l["serve_time"]} to serve\n')
        if l.get("notes"):
            p.text(f'   {l["notes"]}\n')
        p.text("\n")

    p.text(SEPARATOR)
    p.set(align="center")
    p.text(order["datetime"] + "\n\n")

    p.cut()
    p.close()

# ---------------- MAIN ----------------

def main():
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    order = data["order"]

    # COMANDA
    print_comanda(data["printers"]["comanda"], order)

    # FISCAL (SAFE STUB)
    fiscal_cfg = data["printers"]["fiscale"]
    fiscal = DadoRT30Printer(fiscal_cfg["ip"], fiscal_cfg["port"])

    fiscal.open_receipt()
    for l in order["lines"]:
        fiscal.sell_item(l["description"], l["qty"], l["price"], l["vat"])
    for p in order["payments"]:
        fiscal.payment(p["type"], p["amount"])
    fiscal.close_receipt()

    print("Comanda sent. Fiscal receipt prepared (stub).")

if __name__ == "__main__":
    main()
