#!/usr/bin/env python3
"""
Skrypt do przesyłania faktur do ifirma przez API.
Autor: Maciej Szymczak
Copyright (c) 2025 Maciej Szymczak
Licencja: MIT License
Wersja: 1.0.11
"""

__author__ = "Maciej Szymczak"
__copyright__ = "Copyright (c) 2025 Maciej Szymczak"
__license__ = "MIT License"
__version__ = "1.0.11"

import os
import json
import hmac
import hashlib
import requests
from collections import OrderedDict
from dotenv import load_dotenv

DEBUG = True
ADD_NEWLINE = False

load_dotenv()

IFIRMA_API_KEY = os.getenv("IFIRMA_API_KEY", "").strip()
IFIRMA_USERNAME = os.getenv("IFIRMA_USERNAME", "").strip()
IFIRMA_KEY_NAME = os.getenv("IFIRMA_KEY_NAME", "faktura").strip()
IFIRMA_URL = os.getenv("IFIRMA_URL", "https://www.ifirma.pl/iapi/fakturakraj.json").strip()

if not IFIRMA_API_KEY or not IFIRMA_USERNAME:
    raise EnvironmentError("Brak wymaganych zmiennych środowiskowych: IFIRMA_API_KEY lub IFIRMA_USERNAME")

def compute_hmac(message: str, key: str) -> (str, str):
    hmac_obj = hmac.new(key.encode('utf-8'), message.encode('utf-8'), hashlib.sha1)
    return hmac_obj.hexdigest(), hmac_obj.hexdigest().upper()

def order_position(pos: dict) -> OrderedDict:
    keys_order = ["StawkaVat", "Ilosc", "CenaJednostkowa", "NazwaPelna", "Jednostka", "TypStawkiVat"]
    ordered = OrderedDict()
    for key in keys_order:
        if key in pos:
            ordered[key] = pos[key]
    return ordered

def order_contrahent(contr: dict) -> OrderedDict:
    keys_order = ["Nazwa", "Email", "Telefon", "Ulica", "KodPocztowy", "Kraj", "Miejscowosc", "OsobaFizyczna"]
    ordered = OrderedDict()
    for key in keys_order:
        if key in contr:
            ordered[key] = contr[key]
    return ordered

def build_ordered_invoice(invoice: dict) -> OrderedDict:
    # Jeśli pole "Numer" nie istnieje, ustaw je jawnie na None
    if "Numer" not in invoice:
        invoice["Numer"] = None
    keys_order = [
        "Zaplacono",
        "LiczOd",
        "NumerKontaBankowego",
        "DataWystawienia",
        "MiejsceWystawienia",
        "DataSprzedazy",
        "FormatDatySprzedazy",
        "TerminPlatnosci",
        "SposobZaplaty",
        "NazwaSeriiNumeracji",
        "NazwaSzablonu",
        "RodzajPodpisuOdbiorcy",
        "PodpisOdbiorcy",
        "PodpisWystawcy",
        "Uwagi",
        "WidocznyNumerGios",
        "Numer",
        "Pozycje",
        "Kontrahent"
    ]
    ordered = OrderedDict()
    for key in keys_order:
        if key not in invoice:
            continue
        if key == "Pozycje" and isinstance(invoice[key], list):
            ordered_positions = []
            for pos in invoice[key]:
                ordered_positions.append(order_position(pos))
            ordered[key] = ordered_positions
        elif key == "Kontrahent" and isinstance(invoice[key], dict):
            ordered[key] = order_contrahent(invoice[key])
        else:
            ordered[key] = invoice[key]
    return ordered

def upload_invoice(invoice: dict) -> None:
    # Usuń pole "Status" – nie jest częścią specyfikacji ifirma.
    invoice.pop("Status", None)
    
    # Ustaw NumerKontaBankowego na "BRAK", jeśli jest puste.
    if invoice.get("NumerKontaBankowego") is None:
        invoice["NumerKontaBankowego"] = "BRAK"
    
    # Czyść pole "Telefon" w obiekcie Kontrahent.
    kontrahent = invoice.get("Kontrahent", {})
    if "Telefon" in kontrahent:
        kontrahent["Telefon"] = kontrahent["Telefon"].replace("'", "").strip()
        invoice["Kontrahent"] = kontrahent

    # Budujemy uporządkowany obiekt faktury.
    ordered_invoice = build_ordered_invoice(invoice)
    
    # Generujemy ciąg JSON z uporządkowanym obiektem.
    request_content = json.dumps(ordered_invoice, separators=(',', ':'), ensure_ascii=False)
    if ADD_NEWLINE:
        request_content = request_content.rstrip() + "\n"
    else:
        request_content = request_content.rstrip()
    
    # Budujemy ciąg do podpisania: IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content
    message = IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content
    hash_lower, hash_upper = compute_hmac(message, IFIRMA_API_KEY)
    hmac_hash = hash_lower  # używamy lowercase
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "Authentication": f"IAPIS user={IFIRMA_USERNAME}, hmac-sha1={hmac_hash}"
    }
    
    if DEBUG:
        print("=== DEBUG ===")
        print("Request content (JSON):")
        print(request_content)
        print("\nCiąg do podpisania:")
        print(message)
        print("\nObliczony hash (lowercase):")
        print(hash_lower)
        print("Obliczony hash (uppercase):")
        print(hash_upper)
        print("Nagłówki:")
        for key, value in headers.items():
            print(f"{key}: {value}")
        print("=== KONIEC DEBUGU ===\n")
    
    try:
        response = requests.post(IFIRMA_URL, data=request_content.encode('utf-8'), headers=headers, timeout=300)
        response.raise_for_status()
        print(f"Faktura została pomyślnie dodana. Odpowiedź: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Błąd przy wysyłaniu faktury: {e}\nOdpowiedź: {getattr(e, 'response', 'Brak odpowiedzi')}")

def main():
    try:
        with open("ifirma_invoices.json", "r", encoding="utf-8") as f:
            invoices = json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Nie udało się wczytać pliku ifirma_invoices.json: {e}")
    
    print(f"Wczytano {len(invoices)} faktur do przesłania.")
    for invoice in invoices:
        upload_invoice(invoice)

if __name__ == "__main__":
    main()
