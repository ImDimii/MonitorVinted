"""
╔══════════════════════════════════════════════════════════════╗
║               🛍️  VINTED MONITOR + TELEGRAM  🛍️              ║
║                                                              ║
║  Monitora nuovi annunci su Vinted e invia notifiche          ║
║  su Telegram in tempo reale.                                 ║
╚══════════════════════════════════════════════════════════════╝

Uso:
    1. Copia .env.example in .env e inserisci le tue credenziali
    2. pip install -r requirements.txt
    3. python monitor.py
"""

import json
import os
import sys
import time
import random
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

from dotenv import load_dotenv
from curl_cffi import requests as curl_requests

# ─── Logging Setup ────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join("logs", f"monitor_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("VintedMonitor")

# ─── Load Environment ────────────────────────────────────────
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
VINTED_SEARCH_URL = os.getenv(
    "VINTED_SEARCH_URL",
    "https://www.vinted.it/catalog?search_text=Apple%20Watch%2011&order=newest_first&price_from=80&currency=EUR",
)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
BROWSER_IMPERSONATE = os.getenv("BROWSER_IMPERSONATE", "chrome124")

# File per tracciare gli annunci già visti
SEEN_ITEMS_FILE = "seen_items.json"


# ═══════════════════════════════════════════════════════════════
#  TELEGRAM NOTIFIER
# ═══════════════════════════════════════════════════════════════
class TelegramNotifier:
    """Invia notifiche tramite Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Invia un messaggio di testo su Telegram."""
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }
        try:
            resp = curl_requests.post(url, json=payload, impersonate=BROWSER_IMPERSONATE)
            if resp.status_code == 200:
                logger.info("✅ Notifica Telegram inviata!")
                return True
            else:
                logger.error(f"❌ Errore Telegram: {resp.status_code} — {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Errore invio Telegram: {e}")
            return False

    def send_photo(self, photo_url: str, caption: str) -> bool:
        """Invia una foto con didascalia su Telegram."""
        url = f"{self.api_base}/sendPhoto"
        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        }
        try:
            resp = curl_requests.post(url, json=payload, impersonate=BROWSER_IMPERSONATE)
            if resp.status_code == 200:
                logger.info("✅ Foto Telegram inviata!")
                return True
            else:
                logger.warning(f"⚠️ Fallback a messaggio testo (foto fallita: {resp.status_code})")
                return self.send_message(caption)
        except Exception as e:
            logger.warning(f"⚠️ Fallback a messaggio testo (errore foto: {e})")
            return self.send_message(caption)

    def test_connection(self) -> bool:
        """Testa la connessione al bot Telegram."""
        url = f"{self.api_base}/getMe"
        try:
            resp = curl_requests.get(url, impersonate=BROWSER_IMPERSONATE)
            data = resp.json()
            if data.get("ok"):
                bot_name = data["result"].get("username", "Unknown")
                logger.info(f"🤖 Bot Telegram connesso: @{bot_name}")
                return True
            else:
                logger.error(f"❌ Bot Telegram non valido: {data}")
                return False
        except Exception as e:
            logger.error(f"❌ Impossibile connettersi a Telegram: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
#  VINTED SCRAPER
# ═══════════════════════════════════════════════════════════════
class VintedScraper:
    """Accede all'API interna di Vinted per cercare annunci."""

    # Domini Vinted supportati
    DOMAINS = {
        "vinted.it": "https://www.vinted.it",
        "vinted.fr": "https://www.vinted.fr",
        "vinted.de": "https://www.vinted.de",
        "vinted.es": "https://www.vinted.es",
        "vinted.nl": "https://www.vinted.nl",
        "vinted.be": "https://www.vinted.be",
        "vinted.pl": "https://www.vinted.pl",
        "vinted.pt": "https://www.vinted.pt",
        "vinted.co.uk": "https://www.vinted.co.uk",
        "vinted.lt": "https://www.vinted.lt",
        "vinted.cz": "https://www.vinted.cz",
        "vinted.hu": "https://www.vinted.hu",
        "vinted.ro": "https://www.vinted.ro",
        "vinted.lu": "https://www.vinted.lu",
        "vinted.at": "https://www.vinted.at",
        "vinted.sk": "https://www.vinted.sk",
        "vinted.fi": "https://www.vinted.fi",
        "vinted.dk": "https://www.vinted.dk",
        "vinted.se": "https://www.vinted.se",
        "vinted.gr": "https://www.vinted.gr",
        "vinted.hr": "https://www.vinted.hr",
    }

    def __init__(self, search_url: str, impersonate: str = "chrome124"):
        self.impersonate = impersonate
        self.session = None
        self.cookies = {}

        # Parse del URL di ricerca per estrarre dominio e parametri
        parsed = urlparse(search_url)
        self.domain = parsed.hostname  # es. www.vinted.it
        self.base_url = f"{parsed.scheme}://{self.domain}"
        self.search_params = parse_qs(parsed.query)

        # Converte i valori da lista a singolo valore
        self.search_params = {k: v[0] if len(v) == 1 else v for k, v in self.search_params.items()}

        # Rimuovi parametri non necessari per l'API
        self.search_params.pop("page", None)
        self.search_params.pop("time", None)
        self.search_params.pop("search_id", None)

        logger.info(f"🌐 Dominio: {self.base_url}")
        logger.info(f"🔍 Parametri ricerca: {self.search_params}")

    def _create_session(self):
        """Crea una nuova sessione con headers realistici."""
        self.session = curl_requests.Session(impersonate=self.impersonate)
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })

    def _warm_session(self) -> bool:
        """
        Visita la homepage per ottenere cookies di sessione validi.
        Questo è necessario per passare i controlli anti-bot.
        """
        try:
            if self.session is None:
                self._create_session()

            logger.info("🔄 Riscaldamento sessione (visita homepage)...")
            resp = self.session.get(
                self.base_url,
                timeout=30,
            )

            if resp.status_code == 200:
                # Salva i cookies dalla risposta
                self.cookies = dict(resp.cookies)
                logger.info(f"🍪 Cookies ottenuti: {len(self.cookies)} cookie(s)")
                return True
            else:
                logger.warning(f"⚠️ Homepage ritorna status {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Errore riscaldamento sessione: {e}")
            return False

    def fetch_items(self, per_page: int = 20) -> list:
        """
        Recupera gli annunci dall'API Vinted.
        Ritorna una lista di dizionari con i dati degli annunci.
        """
        if self.session is None:
            self._create_session()
            self._warm_session()
            # Piccola pausa per sembrare umano
            time.sleep(random.uniform(1.0, 3.0))

        api_url = f"{self.base_url}/api/v2/catalog/items"

        # Costruisci i parametri di ricerca per l'API
        params = dict(self.search_params)
        params["per_page"] = str(per_page)
        params["order"] = params.get("order", "newest_first")

        try:
            logger.info(f"📡 Richiesta API: {api_url}")
            resp = self.session.get(
                api_url,
                params=params,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                logger.info(f"📦 Trovati {len(items)} annunci")
                return items

            elif resp.status_code == 401:
                logger.warning("🔑 Sessione scaduta, riscaldamento...")
                self._create_session()
                self._warm_session()
                time.sleep(random.uniform(2.0, 4.0))
                return self.fetch_items(per_page)

            elif resp.status_code == 403:
                logger.warning("🚫 Accesso negato (403). Rigenero sessione...")
                self.session = None
                self.cookies = {}
                time.sleep(random.uniform(5.0, 10.0))
                self._create_session()
                self._warm_session()
                time.sleep(random.uniform(2.0, 4.0))
                return self.fetch_items(per_page)

            elif resp.status_code == 429:
                wait_time = random.uniform(30.0, 60.0)
                logger.warning(f"⏳ Rate limited (429). Attendo {wait_time:.0f}s...")
                time.sleep(wait_time)
                return []

            else:
                logger.error(f"❌ Errore API: {resp.status_code}")
                logger.debug(f"Response: {resp.text[:500]}")
                return []

        except Exception as e:
            logger.error(f"❌ Errore fetch: {e}")
            self.session = None
            return []


# ═══════════════════════════════════════════════════════════════
#  SEEN ITEMS TRACKER
# ═══════════════════════════════════════════════════════════════
class SeenItemsTracker:
    """
    Traccia gli annunci già visti per evitare duplicati.
    
    Usa DUE meccanismi di protezione:
    1. Set di ID già visti → evita di re-notificare lo stesso annuncio
    2. Timestamp di cutoff → ignora annunci creati PRIMA dell'avvio del monitor
       (risolve il problema degli annunci vecchi che "salgono" quando
       altri vengono venduti/cancellati)
    """

    def __init__(self, filepath: str = SEEN_ITEMS_FILE):
        self.filepath = filepath
        self.seen_ids: set = set()
        self.cutoff_timestamp: float = 0.0  # Unix timestamp: ignora tutto prima di questo
        self._load()

    def _load(self):
        """Carica gli ID visti e il cutoff dal file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.seen_ids = set(data.get("seen_ids", []))
                    self.cutoff_timestamp = data.get("cutoff_timestamp", 0.0)
                logger.info(
                    f"📂 Caricati {len(self.seen_ids)} annunci già visti "
                    f"(cutoff: {datetime.fromtimestamp(self.cutoff_timestamp).strftime('%Y-%m-%d %H:%M:%S') if self.cutoff_timestamp else 'nessuno'})"
                )
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"⚠️ Errore caricamento seen_items: {e}")
            self.seen_ids = set()
            self.cutoff_timestamp = 0.0

    def _save(self):
        """Salva gli ID visti e il cutoff su file."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(
                    {
                        "seen_ids": list(self.seen_ids),
                        "cutoff_timestamp": self.cutoff_timestamp,
                        "last_updated": datetime.now().isoformat(),
                        "total_count": len(self.seen_ids),
                    },
                    f,
                    indent=2,
                )
        except IOError as e:
            logger.error(f"❌ Errore salvataggio seen_items: {e}")

    def set_cutoff_now(self):
        """Imposta il cutoff al momento attuale."""
        self.cutoff_timestamp = time.time()
        self._save()
        logger.info(
            f"⏱️ Cutoff impostato a: {datetime.fromtimestamp(self.cutoff_timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def update_cutoff(self, timestamp: float):
        """Aggiorna il cutoff se il timestamp è più recente."""
        if timestamp > self.cutoff_timestamp:
            self.cutoff_timestamp = timestamp
            self._save()

    def is_new(self, item_id) -> bool:
        """Controlla se un annuncio è nuovo (mai visto prima)."""
        return str(item_id) not in self.seen_ids

    def is_after_cutoff(self, item_created_ts: float) -> bool:
        """
        Controlla se l'annuncio è stato creato DOPO il cutoff.
        Questo previene false notifiche quando annunci vecchi
        appaiono nei risultati perché altri sono stati venduti/cancellati.
        """
        if self.cutoff_timestamp == 0.0:
            return True  # Nessun cutoff impostato
        return item_created_ts > self.cutoff_timestamp

    def mark_seen(self, item_id):
        """Segna un annuncio come visto."""
        self.seen_ids.add(str(item_id))
        self._save()

    def mark_many_seen(self, item_ids: list):
        """Segna molti annunci come visti (salva una sola volta)."""
        for item_id in item_ids:
            self.seen_ids.add(str(item_id))
        self._save()

    def cleanup(self, max_items: int = 10000):
        """Rimuove vecchi ID per evitare che il file cresca troppo."""
        if len(self.seen_ids) > max_items:
            excess = len(self.seen_ids) - max_items
            items_list = list(self.seen_ids)
            self.seen_ids = set(items_list[excess:])
            self._save()
            logger.info(f"🧹 Pulizia: rimossi {excess} vecchi ID")


# ═══════════════════════════════════════════════════════════════
#  MAIN MONITOR
# ═══════════════════════════════════════════════════════════════
class VintedMonitor:
    """Monitor principale che coordina scraping e notifiche."""

    def __init__(self):
        self.scraper = VintedScraper(VINTED_SEARCH_URL, BROWSER_IMPERSONATE)
        self.notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        self.tracker = SeenItemsTracker()
        self.check_count = 0
        self.new_items_found = 0
        self.errors_count = 0
        self.start_time = datetime.now()

    def _format_item_message(self, item: dict) -> str:
        """Formatta un annuncio per il messaggio Telegram."""
        title = item.get("title", "Senza titolo")
        price = item.get("price", "N/A")
        currency = item.get("currency", "EUR")

        # Gestione prezzo
        if isinstance(price, dict):
            amount = price.get("amount", "N/A")
            currency = price.get("currency_code", currency)
        else:
            amount = price

        brand = item.get("brand_title", "N/D")
        size = item.get("size_title", "N/D")
        url = item.get("url", "")
        if url and not url.startswith("http"):
            url = f"{self.scraper.base_url}{url}"

        # Info venditore
        user = item.get("user", {})
        seller = user.get("login", "Sconosciuto")

        # Condizione
        status = item.get("status", "")

        msg = (
            f"🛍️ <b>Nuovo annuncio trovato!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>{title}</b>\n"
            f"💰 <b>{amount} {currency}</b>\n"
        )

        if brand and brand != "N/D":
            msg += f"🏷️ Marca: {brand}\n"
        if size and size != "N/D":
            msg += f"📏 Taglia: {size}\n"
        msg += (
            f"👤 Venditore: {seller}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href=\"{url}\">Apri su Vinted</a>"
        )

        return msg

    def _get_item_photo(self, item: dict) -> str | None:
        """Estrae l'URL della foto principale dell'annuncio."""
        photo = item.get("photo")
        if photo:
            # Prova diversi campi per la foto
            for key in ["url", "full_size_url", "dominant_color_url"]:
                url = photo.get(key)
                if url:
                    return url

        # Fallback: thumbnails
        photos = item.get("photos", [])
        if photos and isinstance(photos, list):
            return photos[0].get("url")

        return None

    def _send_startup_message(self):
        """Invia sempre un messaggio di avvio quando il monitor parte."""
        search_text = self.scraper.search_params.get("search_text", "N/A")
        seen_count = len(self.tracker.seen_ids)
        self.notifier.send_message(
            "🟢 <b>Monitor Vinted avviato!</b>\n\n"
            f"🔍 Ricerca: <code>{search_text}</code>\n"
            f"📂 Annunci già tracciati: {seen_count}\n"
            f"⏱ Intervallo: ogni {CHECK_INTERVAL} secondi\n\n"
            "Ti avviserò quando trovo nuovi annunci! 🔔"
        )

    @staticmethod
    def _get_item_timestamp(item: dict) -> float:
        """
        Estrae il timestamp di creazione dall'annuncio.
        Vinted usa diversi campi possibili: created_at_ts, created_at, etc.
        """
        # Campo Unix timestamp diretto (più affidabile)
        ts = item.get("created_at_ts")
        if ts:
            try:
                return float(ts)
            except (ValueError, TypeError):
                pass

        # Campo ISO datetime string
        created_at = item.get("created_at")
        if created_at:
            try:
                # Prova parsing ISO format
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                return dt.timestamp()
            except (ValueError, TypeError):
                pass

        # Campo "photo" ha spesso un created_at_ts
        photo = item.get("photo", {})
        if isinstance(photo, dict):
            photo_ts = photo.get("created_at_ts")
            if photo_ts:
                try:
                    return float(photo_ts)
                except (ValueError, TypeError):
                    pass

        # Fallback: usa l'ID come proxy (ID più alti = più recenti)
        # Ritorna 0 per indicare che non abbiamo un timestamp affidabile
        return 0.0

    def check_new_items(self):
        """Controlla se ci sono nuovi annunci."""
        self.check_count += 1
        logger.info(f"🔍 Controllo #{self.check_count}...")

        items = self.scraper.fetch_items()

        if not items:
            logger.info("📭 Nessun annuncio trovato in questa ricerca")
            return

        # ── Prima esecuzione: segna TUTTI come visti e imposta il cutoff ──
        if self.check_count == 1 and len(self.tracker.seen_ids) == 0:
            all_ids = [str(item.get("id", "")) for item in items if item.get("id")]
            self.tracker.mark_many_seen(all_ids)

            # Imposta il cutoff = timestamp dell'annuncio più recente
            # Così qualsiasi annuncio creato PRIMA di ora verrà ignorato
            max_ts = 0.0
            for item in items:
                ts = self._get_item_timestamp(item)
                if ts > max_ts:
                    max_ts = ts

            if max_ts > 0:
                self.tracker.update_cutoff(max_ts)
                logger.info(
                    f"⏱️ Cutoff impostato all'annuncio più recente: "
                    f"{datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                # Fallback: usa il timestamp attuale
                self.tracker.set_cutoff_now()

            logger.info(
                f"📋 Prima esecuzione: {len(all_ids)} annunci segnati come visti (no notifica)"
            )
            return

        # ── Controllo annunci successivi ──
        new_items = []
        skipped_old = 0

        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue

            # 1) Già visto? → Salta
            if not self.tracker.is_new(item_id):
                continue

            # 2) Controlla timestamp di creazione
            item_ts = self._get_item_timestamp(item)

            if item_ts > 0 and not self.tracker.is_after_cutoff(item_ts):
                # Annuncio VECCHIO che è apparso nei risultati perché
                # un altro è stato venduto/cancellato → NON notificare
                skipped_old += 1
                logger.debug(
                    f"⏭️ Annuncio #{item_id} ignorato: creato il "
                    f"{datetime.fromtimestamp(item_ts).strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(prima del cutoff)"
                )
            else:
                # Annuncio davvero NUOVO → notifica!
                new_items.append(item)

                # Aggiorna il cutoff al più recente
                if item_ts > 0:
                    self.tracker.update_cutoff(item_ts)

        # Segna TUTTI gli annunci del fetch come visti
        # (anche quelli vecchi, così non vengono ri-processati)
        all_fetched_ids = [str(item.get("id", "")) for item in items if item.get("id")]
        self.tracker.mark_many_seen(all_fetched_ids)

        if skipped_old > 0:
            logger.info(
                f"⏭️ Ignorati {skipped_old} annunci vecchi "
                f"(apparsi perché altri sono stati venduti/cancellati)"
            )

        if new_items:
            self.new_items_found += len(new_items)
            logger.info(f"🆕 Trovati {len(new_items)} nuovi annunci VERI!")

            for item in new_items:
                msg = self._format_item_message(item)
                photo_url = self._get_item_photo(item)

                if photo_url:
                    self.notifier.send_photo(photo_url, msg)
                else:
                    self.notifier.send_message(msg)

                # Pausa tra notifiche per evitare rate limit Telegram
                time.sleep(random.uniform(0.5, 1.5))
        else:
            logger.info("✅ Nessun nuovo annuncio")

        # Pulizia periodica
        if self.check_count % 100 == 0:
            self.tracker.cleanup()

    def print_status(self):
        """Stampa lo stato del monitor."""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        logger.info(
            f"📊 Status │ Uptime: {hours}h {minutes}m {seconds}s │ "
            f"Controlli: {self.check_count} │ "
            f"Nuovi trovati: {self.new_items_found} │ "
            f"Errori: {self.errors_count}"
        )

    def run(self):
        """Avvia il loop principale del monitor."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🛍️  VINTED MONITOR v1.0                                    ║
║   Monitoraggio annunci + Notifiche Telegram                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)

        # Validazione configurazione
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
            logger.error("❌ TELEGRAM_BOT_TOKEN non configurato! Modifica il file .env")
            sys.exit(1)

        if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "your_chat_id_here":
            logger.error("❌ TELEGRAM_CHAT_ID non configurato! Modifica il file .env")
            sys.exit(1)

        # Test connessione Telegram
        if not self.notifier.test_connection():
            logger.error("❌ Impossibile connettersi al bot Telegram. Controlla il token.")
            sys.exit(1)

        logger.info(f"🔍 URL di ricerca: {VINTED_SEARCH_URL}")
        logger.info(f"⏱️ Intervallo di controllo: {CHECK_INTERVAL}s")
        logger.info(f"🌐 Browser impersonato: {BROWSER_IMPERSONATE}")
        logger.info("─" * 60)
        self._send_startup_message()

        # Loop principale
        try:
            while True:
                try:
                    self.check_new_items()
                except Exception as e:
                    self.errors_count += 1
                    logger.error(f"❌ Errore nel controllo: {e}")

                    # Se troppi errori consecutivi, rigenera la sessione
                    if self.errors_count % 5 == 0:
                        logger.warning("🔄 Troppi errori, rigenero sessione...")
                        self.scraper.session = None
                        time.sleep(random.uniform(10.0, 20.0))

                # Stampa status ogni 10 controlli
                if self.check_count % 10 == 0:
                    self.print_status()

                # Attesa con jitter (variazione casuale per sembrare più umano)
                jitter = random.uniform(-5, 10)
                wait_time = max(30, CHECK_INTERVAL + jitter)
                logger.info(f"💤 Prossimo controllo tra {wait_time:.0f}s...")
                time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("\n👋 Monitor interrotto dall'utente. Arrivederci!")
            self.print_status()


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    monitor = VintedMonitor()
    monitor.run()
