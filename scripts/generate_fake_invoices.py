import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "samples", "generated")
os.makedirs(OUT_DIR, exist_ok=True)

def make_pdf(path, blocks):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "FAKTURA / INVOICE"); y -= 30
    c.setFont("Helvetica", 10)
    for title, lines in blocks:
        c.setFont("Helvetica-Bold", 11); c.drawString(50, y, title); y -= 16
        c.setFont("Helvetica", 10)
        for ln in lines:
            c.drawString(60, y, ln); y -= 14
        y -= 10
    c.showPage(); c.save()

samples = [
    ("invoice1.pdf", [
        ("Dodavatel", ["ACME s.r.o.", "IČO: 12345679", "DIČ: CZ12345679", "Ulice 1, Praha"]),
        ("Platební údaje", ["Variabilní symbol: 2024001234"]),
        ("Datumy", ["Datum vystavení: 12.06.2025", "Splatnost: 26.06.2025", "DUZP: 12.06.2025"]),
        ("Částky", ["Základ daně (bez DPH): 10 000,00 Kč", "DPH 21%: 2 100,00 Kč", "Celkem k úhradě: 12 100,00 Kč"]),
    ]),
    ("invoice2.pdf", [
        ("Supplier", ["Globex Ltd.", "VAT: DE123456789", "Alt-Str. 5, Berlin"]),
        ("Payment", ["VS: 45678901"]),
        ("Dates", ["Issue date: 2025-07-01", "Due date: 2025-07-15", "Tax point: 2025-07-01"]),
        ("Amounts", ["Subtotal: 2,500.00 EUR", "VAT 21%: 525.00 EUR", "Amount due: 3,025.00 EUR"]),
    ]),
    ("invoice3.pdf", [
        ("Dodavatel", ["Alfa s.r.o.", "ICO: 27074358", "DIC: CZ27074358", "Brno"]),
        ("Platební údaje", ["VS: 98765432"]),
        ("Datumy", ["Vystaveno: 1.8.2025", "Splatnost: 15.8.2025", "DUZP: 1.8.2025"]),
        ("Souhrn", ["Bez DPH: 4 150,50 Kč", "DPH: 871,61 Kč", "Celkem: 5 022,11 Kč"]),
    ]),
    ("invoice4.pdf", [
        ("Supplier", ["Omega LLC", "VAT: CZ12345678", "Some Street 7, Prague"]),
        ("Payment", ["Variable symbol: 31415926"]),
        ("Dates", ["Issue: 31/07/2025", "Payment due: 14/08/2025", "Date of taxable supply: 31/07/2025"]),
        ("Total", ["Total: 1,234.56 CZK", "VAT: 259.26 CZK", "Grand total: 1,493.82 CZK"]),
    ]),
    ("invoice5.pdf", [
        ("Dodavatel", ["Delta s.r.o.", "IČO 12345670", "DIČ CZ12345670", "Olomouc"]),
        ("Platební údaje", ["VS: 11223344"]),
        ("Datumy", ["Datum vystavení 10-07-2025", "Splatnost 24-07-2025", "DUZP 10-07-2025"]),
        ("Souhrn", ["Základ daně 850,00 Kč", "DPH 21% 178,50 Kč", "K úhradě 1 028,50 Kč"]),
    ]),
]

os.makedirs(OUT_DIR, exist_ok=True)
for fname, blocks in samples:
    make_pdf(os.path.join(OUT_DIR, fname), blocks)

print(f"Generated {len(samples)} invoices into {OUT_DIR}")
