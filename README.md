# Pretix i iFirma
## Struktura repozytorium

- **convertPretixtoiFirma.py**  
  Skrypt konwertujący dane z pliku CSV (pretix) do formatu JSON zgodnego z API ifirma. Dane wynikowe zapisuje do pliku `ifirma_invoices.json`.

- **uploadToiFirma.py**  
  Skrypt wysyłający wygenerowane faktury do API ifirma. Obsługuje autoryzację za pomocą HMAC-SHA1, pobiera dane z pliku `.env` oraz obsługuje błędy podczas wysyłki.

- **input.csv**  
  Przykładowy plik CSV z danymi zamówień z pretix.  
  Format: kolumny rozdzielone średnikiem (`;`). Wartości liczbowe zapisane są z przecinkiem jako separatorem dziesiętnym.

- **ifirma_invoices.json**  
  Plik wynikowy zawierający faktury w formacie zgodnym z API ifirma – generowany przez skrypt konwertujący.

- **dot-env**  
  Plik przykładowych danych środowiskowych (API ifirma). Aby skrypt działał, należy wykonać:
  ```bash
  cp dot-env .env
  ```
  Następnie edytuj plik .env i uzupełnij swoje dane (klucz API, login, etc.).

- **.gitignore**  
  Plik ignorujący m.in. plik `.env`, pliki CSV i JSON, aby nie trafiły do repozytorium.

- **requirements.txt**  
  Plik zawierający listę wymaganych bibliotek:
  ```text
  python-dotenv
  requests
  ```
## Tworzenie wirtualnego środowiska
Na macOS zalecam korzystanie z wirtualnego środowiska, aby uniknąć problemów z instalacją bibliotek. Wykonaj następujące kroki:
1. ```bash
   python3 -m venv venv
   ```
2. ```bash
   source venv/bin/activate
   ```
   Po aktywacji w konsoli powinien pojawić się prefiks `(venv)`.
3. ```bash
   pip install -r requirements.txt
   ```
## Konfiguracja `.env`
Następnie otwórz plik `.env` i uzupełnij zmienne:

- `IFIRMA_API_KEY` – Twój klucz API
- `IFIRMA_USERNAME` – Twój login
- `IFIRMA_KEY_NAME` – domyślnie faktura
- `IFIRMA_URL` – domyślnie https://www.ifirma.pl/iapi/fakturakraj.json

No i odpal ;]
