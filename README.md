# 🛍️ Vinted Monitor + Telegram

Monitor automatico per Vinted che controlla nuovi annunci e invia notifiche su Telegram in tempo reale.

## Setup rapido

1. Crea ambiente virtuale e installa dipendenze:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Crea `.env` da `.env.example` e inserisci i valori reali:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
VINTED_SEARCH_URL=https://www.vinted.it/catalog?search_text=Apple%20Watch%2011&order=newest_first&price_from=80&currency=EUR
CHECK_INTERVAL=60
BROWSER_IMPERSONATE=chrome124
```

3. Avvia il monitor:

```bash
python monitor.py
```

## Note

- La prima esecuzione marca gli annunci correnti come già visti.
- Dalla seconda esecuzione invia notifiche solo per nuovi annunci.
- I log vengono salvati in `logs/`.
