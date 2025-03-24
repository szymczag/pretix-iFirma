#!/usr/bin/env python3
"""
Nazwa skryptu: convertPretixtoiFirma.py
Opis: Skrypt do konwersji danych z pretix do formatu wymaganego przez API ifirma.
Autor: Maciej Szymczak
Copyright (c) 2025, Maciej Szymczak
Licencja: MIT License
Wersja: 1.0.0
"""

__author__ = "Maciej Szymczak"
__copyright__ = "Copyright (c) 2025, Maciej Szymczak"
__license__ = "MIT License"
__version__ = "1.0.0"

import csv
import json
from datetime import datetime, timedelta

def convert_date(date_str: str, time_str: str) -> (str, datetime):
    """
    Łączy datę i godzinę (pobrane z kolumn CSV) w ciąg ISO (np. "2025-03-23T12:36:11Z")
    i zwraca zarówno napis daty (YYYY-MM-DD), jak i obiekt datetime.
    """
    if not date_str or not time_str:
        raise ValueError(f"Brak daty lub godziny: data='{date_str}', godzina='{time_str}'")
    # Łączymy datę i godzinę; zakładamy, że podane wartości są w formacie "YYYY-MM-DD" i "HH:MM:SS"
    iso_str = f"{date_str}T{time_str}Z"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"Nieprawidłowy format daty i godziny: {iso_str}") from e
    return dt.date().isoformat(), dt

def float_from_str(num_str: str) -> float:
    """
    Konwertuje tekst reprezentujący liczbę, zamieniając przecinek na kropkę.
    Jeśli tekst jest pusty, zwraca 0.0.
    """
    if not num_str:
        return 0.0
    try:
        return float(num_str.replace(",", "."))
    except Exception as e:
        raise ValueError(f"Nie można przekonwertować '{num_str}' na float") from e

def process_csv_to_ifirma_invoices(csv_file: str, output_file: str) -> None:
    """
    Wczytuje dane z pliku CSV (zakładamy, że separator to ";") i przetwarza każdy wiersz
    na obiekt faktury zgodny z API ifirma. Dokument ustawiany jest jako "do potwierdzenia".
    Przy konwersji:
      - Data i godzina zamówienia są łączone w datę wystawienia.
      - Termin płatności to 7 dni po dacie zamówienia.
      - Nazwa produktu jest ustawiana jako "Wejście na wydarzenie {Nazwa wydarzenia}".
      - Cena produktu, VAT i ilość pobierane są z odpowiednich kolumn.
      - Jeśli stawka VAT wynosi 0.00, ustawiany jest typ "ZW" (zwolniona), inaczej "PRC".
      - Dane kontrahenta pobierane są z kolumn: Imię, Nazwisko, Adres, Kod pocztowy, Miasto, Kraj, Email, Numer telefonu.
    Wynik zapisuje do pliku JSON.
    """
    invoices = []
    with open(csv_file, mode='r', encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            try:
                # Pobieranie danych podstawowych
                order_code = row.get("Kod zamówienia", "").strip()
                date_order = row.get("Data zamówienia", "").strip()
                time_order = row.get("Godzina zamówienia", "").strip()
                email = row.get("Email", "").strip()
                phone = row.get("Numer telefonu", "").strip()
                total = float_from_str(row.get("Suma zamówienia", "0,00").strip())

                # Ustalenie nazwy produktu na podstawie "Nazwa wydarzenia"
                event_name = row.get("Nazwa wydarzenia", "Wydarzenie").strip()
                product_name = f"Wejście na wydarzenie {event_name}"

                # Cena produktu – jeśli istnieje kolumna "Brutto dla podatku 0.00 %", inaczej używamy całkowitej sumy
                product_price = float_from_str(row.get("Brutto dla podatku 0.00 %", "").strip() or row.get("Suma zamówienia", "0,00").strip())
                # Stawka VAT – z kolumny "Wartość podatku 0.00 %"
                tax_rate = float_from_str(row.get("Wartość podatku 0.00 %", "0,00").strip())
                # Ilość – z kolumny "Pozycje"
                quantity = float_from_str(row.get("Pozycje", "1").strip())

                # Łączenie daty i godziny zamówienia
                invoice_date, order_dt = convert_date(date_order, time_order)
                payment_deadline = (order_dt + timedelta(days=7)).date().isoformat()

                # Określenie typu stawki VAT: "ZW" dla 0.00, inaczej "PRC"
                vat_type = "ZW" if tax_rate == 0.0 else "PRC"

                # Budowa pozycji faktury
                position = {
                    "StawkaVat": tax_rate,
                    "Ilosc": quantity,
                    "CenaJednostkowa": product_price,
                    "NazwaPelna": product_name,
                    "Jednostka": "sztuk",
                    "TypStawkiVat": vat_type
                }

                # Budowa danych kontrahenta z CSV – łączymy Imię i Nazwisko oraz pobieramy adres
                first_name = row.get("Imię", "").strip()
                last_name = row.get("Nazwisko", "").strip()
                full_name = f"{first_name} {last_name}".strip() or email or "Klient"
                kontrahent = {
                    "Nazwa": full_name,
                    "Email": email,
                    "Telefon": phone,
                    "Ulica": row.get("Adres", "Nieznana").strip(),
                    "KodPocztowy": row.get("Kod pocztowy", "00-000").strip(),
                    "Kraj": row.get("Kraj", "PL").strip(),
                    "Miejscowosc": row.get("Miasto", "Nieznane").strip(),
                    "OsobaFizyczna": True
                }

                # Budowa obiektu faktury zgodnie z wymaganiami ifirma
                invoice = {
                    "Status": "DO_POTWIERDZENIA",       # Import jako "do potwierdzenia"
                    "Zaplacono": total,
                    "LiczOd": "BRT",                    # Wartość brutto
                    "NumerKontaBankowego": None,
                    "DataWystawienia": invoice_date,
                    "MiejsceWystawienia": row.get("Adres", "Nieznany").strip() or "Nieznane",
                    "DataSprzedazy": invoice_date,
                    "FormatDatySprzedazy": "DZN",        # Format dzienny
                    "TerminPlatnosci": payment_deadline,
                    "SposobZaplaty": "PRZ",              # Przelew
                    "NazwaSeriiNumeracji": "default",
                    "NazwaSzablonu": "",
                    "RodzajPodpisuOdbiorcy": "OUP",
                    "PodpisOdbiorcy": "Odbiorca",
                    "PodpisWystawcy": "Wystawca",
                    "Uwagi": order_code,                # Kod zamówienia jako uwaga
                    "WidocznyNumerGios": True,
                    "Numer": None,
                    "Pozycje": [position],
                    "Kontrahent": kontrahent
                }
                invoices.append(invoice)
            except Exception as e:
                print(f"Błąd przy konwersji zamówienia '{row.get('Kod zamówienia', 'Brak kodu')}': {e}")

    # Zapis wyniku do pliku JSON przy kodowaniu UTF-8 (bez BOM)
    with open(output_file, mode='w', encoding="utf-8") as out_f:
        json.dump(invoices, out_f, indent=4, ensure_ascii=False)
    print(f"Skonwertowano {len(invoices)} zamówień do formatu ifirma. Wynik zapisano do {output_file}")

if __name__ == "__main__":
    input_csv = "input.csv"             # Plik wejściowy CSV
    output_json = "ifirma_invoices.json"  # Plik wynikowy JSON
    process_csv_to_ifirma_invoices(input_csv, output_json)
