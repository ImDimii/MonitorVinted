# 🛍️ Vinted Monitor + Telegram

Monitor automatico per Vinted che controlla nuovi annunci e invia notifiche su Telegram in tempo reale.

## ✨ Funzionalità

- 🔍 Monitora qualsiasi ricerca Vinted (basta copiare l'URL dal browser)
- 📱 Notifiche Telegram istantanee con foto, prezzo e link diretto
- 🔄 Gestione automatica sessione e anti-bot bypass
- 🧠 Tracciamento annunci visti (niente duplicati)
- 📊 Logging dettagliato con status periodico
- 🌐 Supporto multi-paese (tutti i domini Vinted)

## 🚀 Setup Rapido

### 1. Clona/Scarica il progetto

```bash
cd MonitorVinted
```

### 2. Crea virtual environment e installa dipendenze

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configura le credenziali

```bash
# Copia il file di esempio
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```

Apri `.env` e inserisci:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
VINTED_SEARCH_URL=https://www.vinted.it/catalog?search_text=Apple%20Watch%2011&order=newest_first&price_from=80&currency=EUR
CHECK_INTERVAL=60
```

### 4. Avvia il monitor

```bash
python monitor.py
```

### 5. Dashboard web (modifica `.env` + log live)

In un secondo terminale:

```bash
python dashboard.py
```

Poi apri:

```text
http://localhost:5000
```

Da questa pagina puoi:
- modificare le variabili `.env` principali;
- vedere gli ultimi log del monitor in stile terminale (auto-refresh ogni 5 secondi).

## 🔑 Come ottenere le credenziali Telegram

### Bot Token
1. Apri Telegram e cerca **@BotFather**
2. Invia `/newbot` e segui le istruzioni
3. Copia il token che ti viene fornito

### Chat ID
1. Apri Telegram e cerca **@userinfobot**
2. Invia `/start` — ti mostrerà il tuo Chat ID
3. Oppure usa **@getmyid_bot**

## 🖥️ Deploy su Webdock (VPS Linux)

### Metodo automatico

```bash
# Carica i files sul server
scp -r ./* user@tuo-server:/tmp/vinted-monitor/
scp .env user@tuo-server:/tmp/vinted-monitor/

# SSH nel server
ssh user@tuo-server
cd /tmp/vinted-monitor

# Esegui lo script di deploy
chmod +x deploy.sh
./deploy.sh
```

### Comandi utili dopo il deploy

| Comando | Descrizione |
|---------|-------------|
| `sudo systemctl status vinted-monitor` | Controlla lo stato |
| `sudo systemctl restart vinted-monitor` | Riavvia il monitor |
| `sudo systemctl stop vinted-monitor` | Ferma il monitor |
| `sudo journalctl -u vinted-monitor -f` | Vedi i log in tempo reale |

## ▲ Deploy Dashboard su Vercel

Questo progetto include già:
- `api/index.py` (entrypoint Flask per Vercel);
- `vercel.json` (routing verso la dashboard).

### Deploy

```bash
npm i -g vercel
vercel
```

Al termine avrai un link pubblico tipo `https://nome-progetto.vercel.app`.

### Importante su Vercel

- Vercel non è adatto a eseguire `monitor.py` in loop continuo 24/7 (funzioni serverless con timeout).
- La dashboard su Vercel è utile per UI/API, ma i file locali (`.env`, `logs`) in ambiente serverless sono temporanei.
- Per monitor sempre attivo, tieni `monitor.py` su VPS (Webdock/Render/Railway) e usa Vercel solo per il frontend/API verso uno storage persistente.

## ⚠️ Note Importanti

- **Anti-bot**: Vinted usa protezioni avanzate (DataDome). Il monitor gestisce automaticamente il refresh della sessione, ma se ricevi troppi errori 403 potresti aver bisogno di proxy residenziali.
- **Rate limiting**: L'intervallo minimo consigliato è 60 secondi per evitare ban.
- **Prima esecuzione**: Al primo avvio, gli annunci esistenti vengono segnati come "già visti" senza inviarti notifica. Da quel momento in poi riceverai solo i nuovi.

## 📁 Struttura Progetto

```
MonitorVinted/
├── monitor.py          # Script principale
├── requirements.txt    # Dipendenze Python
├── deploy.sh           # Script deploy per Webdock
├── .env.example        # Template configurazione
├── .env                # Le tue credenziali (da creare)
├── .gitignore          # Files da ignorare
├── seen_items.json     # Annunci già visti (auto-generato)
└── logs/               # Log giornalieri (auto-generati)
```
