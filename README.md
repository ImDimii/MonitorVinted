# 🛍️ Vinted Monitor + Telegram (Vercel + cron-job.org)

Monitor Vinted compatibile con Vercel: controlla annunci a intervalli automatici usando cron-job.org e invia notifiche su Telegram.

## Come funziona

- `cron-job.org` chiama `/api/run-now` a intervalli.
- L'endpoint legge gli annunci Vinted.
- I nuovi annunci vengono notificati su Telegram.
- Lo stato (`seen items`, cutoff, contatori) viene salvato in `Upstash Redis`, quindi resta persistente.

## Variabili ambiente richieste

Configura queste variabili su Vercel (`Project Settings -> Environment Variables`):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `VINTED_SEARCH_URL`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `CRON_SECRET`

Opzionale:

- `MAX_ITEMS_PER_RUN` (default `20`)

Template completo in `.env.example`.

## Deploy su Vercel

1. Push su GitHub.
2. Importa il repository in Vercel.
3. Imposta tutte le environment variables.
4. Redeploy.

`vercel.json` è compatibile con piano Hobby (senza cron interno Vercel).

## Endpoint disponibili

- `GET /api/status` → stato monitor
- `POST /api/run-now` → esegue un check manuale (header `Authorization: Bearer <CRON_SECRET>`)
- `GET /api/run-now?secret=<CRON_SECRET>` → endpoint per cron-job.org

## Test rapido post-deploy

1. Apri la root del sito: mostra lo stato base.
2. Apri `/api/status`: verifica `ok: true`.
3. Trigger manuale:

```bash
curl -X POST https://tuo-progetto.vercel.app/api/run-now \
  -H "Authorization: Bearer TUO_CRON_SECRET"
```

4. Configura cron-job.org:

- URL: `https://tuo-progetto.vercel.app/api/run-now?secret=TUO_CRON_SECRET`
- Request method: `GET`
- Schedule: ogni 1 minuto (o quello che preferisci)

5. Controlla se arriva la notifica Telegram.

## Note

- La prima esecuzione inizializza lo stato senza notificare gli annunci già presenti.
- Dal secondo run in poi notifica solo gli annunci davvero nuovi.
- È mantenuta anche la versione Python locale (`monitor.py`), ma il deploy Vercel ora usa la versione JavaScript serverless.
