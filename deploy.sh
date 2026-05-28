#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Script di deploy per Webdock (VPS Linux)
#  
#  Uso: 
#    chmod +x deploy.sh
#    ./deploy.sh
# ═══════════════════════════════════════════════════════════════

set -e

echo "🚀 Deploy Vinted Monitor su Webdock..."

# Installa dipendenze sistema
echo "📦 Aggiornamento pacchetti..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv

# Crea directory progetto
PROJECT_DIR="/opt/vinted-monitor"
sudo mkdir -p "$PROJECT_DIR"
sudo chown $USER:$USER "$PROJECT_DIR"

# Copia files (se non stai usando git)
echo "📂 Copia files..."
cp -r ./* "$PROJECT_DIR/" 2>/dev/null || true
cp .env "$PROJECT_DIR/" 2>/dev/null || true

cd "$PROJECT_DIR"

# Crea virtual environment
echo "🐍 Creazione virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze
echo "📥 Installazione dipendenze..."
pip install --upgrade pip
pip install -r requirements.txt

# Crea il servizio systemd
echo "⚙️ Configurazione servizio systemd..."
sudo tee /etc/systemd/system/vinted-monitor.service > /dev/null << EOF
[Unit]
Description=Vinted Monitor - Notifiche Telegram
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/monitor.py
Restart=always
RestartSec=30
StandardOutput=append:$PROJECT_DIR/logs/stdout.log
StandardError=append:$PROJECT_DIR/logs/stderr.log

# Sicurezza
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Crea directory logs
mkdir -p "$PROJECT_DIR/logs"

# Abilita e avvia il servizio
echo "🟢 Avvio servizio..."
sudo systemctl daemon-reload
sudo systemctl enable vinted-monitor.service
sudo systemctl start vinted-monitor.service

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ Deploy completato!                              ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Comandi utili:                                      ║"
echo "║                                                      ║"
echo "║  📊 Status:  sudo systemctl status vinted-monitor    ║"
echo "║  📋 Logs:    sudo journalctl -u vinted-monitor -f    ║"
echo "║  🔄 Restart: sudo systemctl restart vinted-monitor   ║"
echo "║  ⏹  Stop:    sudo systemctl stop vinted-monitor      ║"
echo "║  📝 Log app: tail -f $PROJECT_DIR/logs/*.log         ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
