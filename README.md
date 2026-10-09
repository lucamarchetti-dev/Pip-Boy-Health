# Pip-Boy Health

Monitor dello stato di salute di un server, con script a riga di comando e dashboard web.

Il progetto rileva **CPU, RAM, spazio disco e ultime righe del log di sistema**, salva i dati in file di report e in un database SQLite, e **manda un alert quando il disco supera l'80%**. Una dashboard Django mostra i valori più recenti, l'andamento nel tempo e una tabella delle ultime rilevazioni con i valori critici in rosso.

## Cosa include

**Parte 1 – Script e OOP (`system_monitor.py`)**
- Classe `SystemMonitor` che legge i valori reali con `psutil` oppure li simula (`--simulate`).
- Report in `reports/metrics.json` e `reports/metrics.csv`, aggiornati a ogni rilevazione.
- Alert se il disco supera la soglia (default 80%): log in `reports/alerts.log`, messaggio Telegram e/o richiesta HTTP verso un webhook.

**Parte 2 – Web app (Django + SQLite)**
- Modello `ServerMetric` salvato nel database SQLite di Django (`db.sqlite3`).
- Tracciato ECG animato: verde e lento se tutto è nella norma, rosso e rapido se un valore è critico.
- Tre indicatori ad anello (CPU, RAM, disco) con la soglia segnata da una tacca.
- Grafico delle ultime 20 rilevazioni, con tooltip e legenda cliccabile.
- Tabella con celle critiche in rosso (disco > 80%, CPU e RAM > 85%), filtro «Solo critiche» e log espandibile.
- Aggiornamento automatico ogni 15 secondi con pulsante di pausa, notifiche, tema chiaro e scuro.
- Funziona anche offline: nessuna libreria o font esterni.
- Pannello `/admin/` e endpoint JSON `/api/metrics/`.

## Requisiti
- Python 3.10 o superiore
- Dipendenze in `requirements.txt` (Django e psutil)

## Avvio rapido

### Linux e macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py collect_metrics --simulate --count 10
python manage.py runserver
```

### Windows (Prompt dei comandi)
```cmd
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt

python manage.py migrate
python manage.py collect_metrics --simulate --count 10
python manage.py runserver
```

### Windows (PowerShell)
```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # una sola volta
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python manage.py migrate
python manage.py collect_metrics --simulate --count 10
python manage.py runserver
```

Poi apri **http://127.0.0.1:8000/** nel browser. Per fermare il server premi `Ctrl+C`.
Quando l'ambiente virtuale è attivo, il terminale mostra `(.venv)` all'inizio della riga.
Dalla seconda volta basta riattivare l'ambiente e lanciare `python manage.py runserver`.

## Uso

### Script da riga di comando
```bash
python system_monitor.py                        # misure reali
python system_monitor.py --simulate             # valori casuali
python system_monitor.py --simulate --disk 92   # forza il disco al 92% e fa scattare l'alert
python system_monitor.py --threshold 70         # cambia la soglia del disco
```
Su Windows usa gli stessi comandi con `python` (o `py`).

### Web app
- **Rileva ora**: misura i valori reali del computer e li salva nel database.
- **Rileva con dati simulati**: salva una rilevazione con valori casuali, utile per provare la dashboard.
- `python manage.py collect_metrics [--simulate] [--disk 92] [--count 5]`: stessa cosa da terminale.
- `python manage.py createsuperuser`: crea un utente per accedere a `/admin/`.

### Rilevazione periodica
- **Linux/macOS** (cron): `*/5 * * * * cd /percorso/system_health && .venv/bin/python manage.py collect_metrics`
- **Windows**: crea un'attività in *Utilità di pianificazione* che esegue `.venv\Scripts\python.exe manage.py collect_metrics` nella cartella del progetto.

## Alert (facoltativi)

Senza configurazione, gli alert finiscono solo nel log. Per riceverli altrove imposta le variabili d'ambiente prima di avviare lo script o il server.

| Variabile | Effetto |
|---|---|
| `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` | messaggio Telegram |
| `ALERT_WEBHOOK_URL` | richiesta HTTP POST con corpo `{"text": "..."}` |

| Sistema | Esempio |
|---|---|
| Linux/macOS | `export TELEGRAM_BOT_TOKEN="123456:ABC..."` |
| Windows cmd | `set TELEGRAM_BOT_TOKEN=123456:ABC...` |
| Windows PowerShell | `$env:TELEGRAM_BOT_TOKEN="123456:ABC..."` |

**Come ottenere i valori Telegram**
1. Su Telegram apri **@BotFather**, scrivi `/newbot` e segui le istruzioni: ti darà il token.
2. Avvia il tuo bot e scrivigli un messaggio qualsiasi.
3. Apri `https://api.telegram.org/botIL_TOKEN/getUpdates` e cerca `"chat":{"id":...}`: quel numero è il `TELEGRAM_CHAT_ID`.

Il formato del webhook è quello atteso da Slack e Mattermost. Discord richiede invece la chiave `content`. Il token è come una password: non pubblicarlo.

## Soglie
Si modificano all'inizio di `system_monitor.py`:
- `DISK_ALERT_THRESHOLD = 80.0`: soglia di alert del disco
- `CPU_WARN_THRESHOLD = 85.0` e `RAM_WARN_THRESHOLD = 85.0`: usate per colorare la dashboard

## Struttura del progetto
```
PBH_ProgettoPython/
├── system_monitor.py          classe SystemMonitor (script standalone)
├── manage.py
├── requirements.txt
├── config/                    impostazioni Django (SQLite, lingua italiana)
├── metrics/
│   ├── models.py              modello ServerMetric
│   ├── services.py            collega SystemMonitor al database
│   ├── views.py, urls.py      dashboard, rilevazione, API JSON
│   ├── admin.py
│   ├── management/commands/   comando collect_metrics
│   ├── migrations/
│   ├── templates/metrics/     dashboard.html
│   ├── static/metrics/        dashboard.css, dashboard.js
│   └── tests.py               test Django
├── tests/                     test dello script
└── reports/                   metrics.json, metrics.csv, alerts.log
```

## Test
```bash
python -m unittest discover -s tests    # script SystemMonitor
python manage.py test                   # parte Django
```

## Problemi comuni

| Problema | Soluzione |
|---|---|
| `source` non è riconosciuto (Windows) | Usa `.venv\Scripts\activate.bat`: `source` esiste solo su Linux e macOS |
| `Set-ExecutionPolicy` non riconosciuto | Stai usando cmd, non PowerShell: salta quel comando |
| «Impossibile trovare il percorso» attivando l'ambiente | L'ambiente non esiste ancora: esegui prima `py -m venv .venv` |
| `py` o `python` non riconosciuti | Reinstalla Python da python.org spuntando «Add python.exe to PATH» |
| La pagina non cambia dopo un aggiornamento dei file | Premi `Ctrl+F5` per svuotare la cache del browser |
| Il pulsante «Rileva ora» dà errore | Guarda il terminale di `runserver`: l'errore è scritto lì |
| CPU sempre a 0% | `psutil` non è installato: `pip install psutil` |
| Nessun log di sistema reale su Windows | Normale: `/var/log/syslog` esiste solo su Linux, su Windows vengono mostrate righe di esempio |

## Note
- `DEBUG` è attivo e la chiave segreta è quella di sviluppo: va bene in locale, ma per un uso reale imposta `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS`.
- I dati restano salvati anche dopo la chiusura del server. Per ripartire da zero cancella `db.sqlite3` e riesegui `python manage.py migrate`.
