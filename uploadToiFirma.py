#!/usr/bin/env python3
"""
Skrypt do przesyłania faktur do ifirma przez API.
Autor: Maciej Szymczak
Copyright (c) 2025 Maciej Szymczak
Licencja: MIT License
Wersja: 2.0
"""

__author__ = "Maciej Szymczak"
__copyright__ = "Copyright (c) 2025 Maciej Szymczak"
__license__ = "MIT License"
__version__ = "2.0"

import os
import json
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

IFIRMA_API_KEY = os.getenv("IFIRMA_API_KEY", "").strip()
IFIRMA_USERNAME = os.getenv("IFIRMA_USERNAME", "").strip()
IFIRMA_KEY_NAME = os.getenv("IFIRMA_KEY_NAME", "faktura").strip()
IFIRMA_URL = os.getenv("IFIRMA_URL", "https://www.ifirma.pl/iapi/fakturakraj.json").strip()

if not IFIRMA_API_KEY or not IFIRMA_USERNAME:
    raise EnvironmentError("Brak wymaganych zmiennych środowiskowych: IFIRMA_API_KEY lub IFIRMA_USERNAME")

def get_dates():
    """Zwraca dzisiejszą datę oraz termin płatności (dzisiaj + 7 dni) w formacie YYYY-MM-DD."""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    deadline_str = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    return today_str, deadline_str

def compute_hmac(message: str, key_bytes: bytes) -> str:
    """Oblicza HMAC-SHA1 dla podanego komunikatu z użyciem klucza (w bajtach) i zwraca wynik jako ciąg hex (lowercase)."""
    hmac_obj = hmac.new(key_bytes, message.encode('utf-8'), hashlib.sha1)
    return hmac_obj.hexdigest()

def remove_none_values(d: dict) -> dict:
    """Rekurencyjnie usuwa z obiektu dict klucze z wartością None."""
    if not isinstance(d, dict):
        return d
    return {k: remove_none_values(v) for k, v in d.items() if v is not None}

def order_position(pos: dict) -> dict:
    """
    Jeśli TypStawkiVat ma wartość "ZW", ustaw StawkaVat na None.
    """
    if pos.get("TypStawkiVat") == "ZW":
        pos["StawkaVat"] = None
    return pos

def upload_invoice(invoice: dict) -> None:
    # Usuwamy pole "Status", jeśli istnieje.
    invoice.pop("Status", None)
    # Jeśli NumerKontaBankowego jest pusty, ustawiamy na "BRAK".
    if invoice.get("NumerKontaBankowego") is None:
        invoice["NumerKontaBankowego"] = "BRAK"
    # Czyszczenie pola "Telefon" w obiekcie Kontrahent.
    if "Kontrahent" in invoice and isinstance(invoice["Kontrahent"], dict):
        if "Telefon" in invoice["Kontrahent"]:
            invoice["Kontrahent"]["Telefon"] = invoice["Kontrahent"]["Telefon"].replace("'", "").strip()

    # Nadpisujemy daty na bieżące.
    today_str, deadline_str = get_dates()
    invoice["DataWystawienia"] = today_str
    invoice["DataSprzedazy"] = today_str
    invoice["TerminPlatnosci"] = deadline_str

    # Dla każdej pozycji faktury, ustawiamy StawkaVat na None, jeśli TypStawkiVat == "ZW".
    if "Pozycje" in invoice and isinstance(invoice["Pozycje"], list):
        invoice["Pozycje"] = [order_position(pos) for pos in invoice["Pozycje"]]

    invoice = remove_none_values(invoice)
    request_content = json.dumps(invoice, separators=(',', ':'), ensure_ascii=False).rstrip()

    # Budujemy ciąg do podpisania: IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content
    message = IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content

    # Konwertujemy klucz API z postaci heksadecymalnej na bajty.
    key_bytes = bytes.fromhex(IFIRMA_API_KEY)
    hmac_hash = compute_hmac(message, key_bytes)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "Authentication": f"IAPIS user={IFIRMA_USERNAME}, hmac-sha1={hmac_hash}"
    }

    try:
        response = requests.post(IFIRMA_URL, data=request_content.encode('utf-8'), headers=headers, timeout=300)
        response.raise_for_status()
        # Wyświetl informacje o fakturze, dla której wykonano żądanie.
        print(f"Faktura (kod: {invoice.get('Uwagi')}, kontrahent: {invoice.get('Kontrahent', {}).get('Nazwa')}) została dodana. Odpowiedź: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Błąd przy wysyłaniu faktury (kod: {invoice.get('Uwagi')}, kontrahent: {invoice.get('Kontrahent', {}).get('Nazwa')}): {e}\nOdpowiedź: {getattr(e, 'response', 'Brak odpowiedzi')}")

def main():
    with open("ifirma_invoices.json", "r", encoding="utf-8") as f:
        invoices = json.load(f)
    print(f"Wczytano {len(invoices)} faktur do przesłania.")
    for invoice in invoices:
        upload_invoice(invoice)

if __name__ == "__main__":
    main()
