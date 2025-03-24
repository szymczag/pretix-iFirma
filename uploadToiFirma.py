#!/usr/bin/env python3
"""
Nazwa skryptu: uploadToiFirma.py
Opis: Skrypt do masowego tworzenia faktur w iFirma za pomocą API, bazując na przygotowanym pliku JSON.
Autor: Maciej Szymczak
Copyright (c) 2025, Maciej Szymczak
Licencja: MIT License
Wersja: 1.0.0
"""

__author__ = "Maciej Szymczak"
__copyright__ = "Copyright (c) 2025, Maciej Szymczak"
__license__ = "MIT License"
__version__ = "1.0.0"

import os
import json
import hmac
import hashlib
import requests
from dotenv import load_dotenv

# Ładujemy zmienne środowiskowe z pliku .env
load_dotenv()

IFIRMA_API_KEY = os.getenv("IFIRMA_API_KEY")
IFIRMA_USERNAME = os.getenv("IFIRMA_USERNAME")
IFIRMA_KEY_NAME = os.getenv("IFIRMA_KEY_NAME", "faktura")
IFIRMA_URL = os.getenv("IFIRMA_URL", "https://www.ifirma.pl/iapi/fakturakraj.json")

# Walidacja wymaganych zmiennych
if not IFIRMA_API_KEY or not IFIRMA_USERNAME:
    raise EnvironmentError("Brak wymaganych zmiennych środowiskowych: IFIRMA_API_KEY lub IFIRMA_USERNAME")

def compute_hmac(message: str, key: str) -> str:
    """
    Oblicza HMAC-SHA1 dla podanego komunikatu przy użyciu klucza.
    """
    digest = hmac.new(key.encode('utf-8'), message.encode('utf-8'), hashlib.sha1).hexdigest()
    return digest

def upload_invoice(invoice: dict) -> None:
    """
    Wysyła pojedynczą fakturę (jako JSON) do API ifirma.
    Oblicza podpis HMAC na podstawie:
      IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content
    oraz wysyła żądanie POST z odpowiednimi nagłówkami.
    """
    # Używamy minimalnego formatu JSON (bez zbędnych spacji)
    request_content = json.dumps(invoice, separators=(',', ':'), ensure_ascii=False)

    # Budujemy komunikat do podpisania
    message = IFIRMA_URL + IFIRMA_USERNAME + IFIRMA_KEY_NAME + request_content
    hmac_hash = compute_hmac(message, IFIRMA_API_KEY)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "Authentication": f"IAPIS user={IFIRMA_USERNAME}, hmac-sha1={hmac_hash}"
    }

    try:
        response = requests.post(IFIRMA_URL, data=request_content.encode('utf-8'), headers=headers, timeout=300)
        response.raise_for_status()
        print(f"Faktura została pomyślnie dodana. Odpowiedź: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Błąd przy wysyłaniu faktury: {e}\nOdpowiedź: {getattr(e, 'response', 'Brak odpowiedzi')}")

def main():
    # Wczytujemy faktury z pliku JSON
    try:
        with open("ifirma_invoices.json", "r", encoding="utf-8") as f:
            invoices = json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Nie udało się wczytać pliku ifirma_invoices.json: {e}")

    print(f"Wczytano {len(invoices)} faktur do przesłania.")

    # Wysyłamy faktury pojedynczo
    for invoice in invoices:
        upload_invoice(invoice)

if __name__ == "__main__":
    main()
