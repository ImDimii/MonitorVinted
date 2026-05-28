import glob
import os
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

ENV_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "VINTED_SEARCH_URL",
    "CHECK_INTERVAL",
    "BROWSER_IMPERSONATE",
]

app = Flask(__name__)


def parse_env_file(path: str) -> dict:
    values = {key: "" for key in ENV_KEYS}
    if not os.path.exists(path):
        return values

    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in values:
                values[key] = value.strip()
    return values


def write_env_file(path: str, values: dict) -> None:
    lines = [f"{key}={values.get(key, '')}" for key in ENV_KEYS]
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def latest_log_file() -> str | None:
    if not os.path.isdir(LOGS_DIR):
        return None
    files = glob.glob(os.path.join(LOGS_DIR, "monitor_*.log"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def read_last_log_lines(max_lines: int = 150) -> tuple[str, str]:
    log_path = latest_log_file()
    if not log_path:
        return "Nessun log disponibile.", ""

    with open(log_path, "r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()

    last_lines = lines[-max_lines:]
    filename = os.path.basename(log_path)
    return "".join(last_lines), filename


HTML_PAGE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monitor Vinted Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #111827; color: #f3f4f6; }
    h1, h2 { margin-bottom: 10px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 20px; }
    .card { background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 16px; }
    label { display: block; margin-bottom: 6px; font-size: 14px; color: #d1d5db; }
    input { width: 100%; margin-bottom: 12px; padding: 10px; border-radius: 8px; border: 1px solid #4b5563; background: #111827; color: #f9fafb; }
    button { background: #2563eb; color: white; border: none; padding: 10px 14px; border-radius: 8px; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .status { margin-top: 10px; font-size: 14px; color: #93c5fd; min-height: 18px; }
    pre { background: #030712; border: 1px solid #374151; border-radius: 10px; padding: 14px; overflow: auto; max-height: 500px; font-size: 12px; line-height: 1.4; }
    .muted { color: #9ca3af; font-size: 13px; }
  </style>
</head>
<body>
  <h1>Monitor Vinted - Dashboard Web</h1>
  <p class="muted">Modifica file .env e visualizza gli ultimi log del monitor.</p>

  <div class="grid">
    <div class="card">
      <h2>Configurazione .env</h2>
      <form id="env-form">
        {% for key in env_keys %}
          <label for="{{ key }}">{{ key }}</label>
          <input id="{{ key }}" name="{{ key }}" value="{{ env_values.get(key, '') }}">
        {% endfor %}
        <button type="submit">Salva configurazione</button>
        <div id="save-status" class="status"></div>
      </form>
    </div>

    <div class="card">
      <h2>Log monitor (stile terminale)</h2>
      <p class="muted">File corrente: <span id="log-file">{{ log_filename or 'nessuno' }}</span></p>
      <pre id="log-output">{{ log_output }}</pre>
    </div>
  </div>

  <script>
    const envForm = document.getElementById("env-form");
    const saveStatus = document.getElementById("save-status");
    const logOutput = document.getElementById("log-output");
    const logFile = document.getElementById("log-file");

    envForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      saveStatus.textContent = "Salvataggio in corso...";
      const formData = new FormData(envForm);
      const payload = {};
      for (const [key, value] of formData.entries()) {
        payload[key] = value;
      }

      const res = await fetch("/api/env", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        saveStatus.textContent = "Errore nel salvataggio.";
        return;
      }

      const json = await res.json();
      saveStatus.textContent = json.message + " (" + new Date().toLocaleTimeString() + ")";
    });

    async function refreshLogs() {
      const res = await fetch("/api/logs");
      if (!res.ok) {
        return;
      }

      const json = await res.json();
      logOutput.textContent = json.log_output;
      logFile.textContent = json.log_filename || "nessuno";
      logOutput.scrollTop = logOutput.scrollHeight;
    }

    setInterval(refreshLogs, 5000);
  </script>
</body>
</html>
"""


@app.get("/")
def dashboard_home():
    env_values = parse_env_file(ENV_PATH)
    log_output, log_filename = read_last_log_lines()
    return render_template_string(
        HTML_PAGE,
        env_keys=ENV_KEYS,
        env_values=env_values,
        log_output=log_output,
        log_filename=log_filename,
    )


@app.get("/api/env")
def get_env_values():
    return jsonify(parse_env_file(ENV_PATH))


@app.post("/api/env")
def save_env_values():
    payload = request.get_json(silent=True) or {}
    values = parse_env_file(ENV_PATH)
    for key in ENV_KEYS:
        if key in payload:
            values[key] = str(payload[key]).strip()

    write_env_file(ENV_PATH, values)
    return jsonify(
        {
            "message": "Configurazione salvata. Riavvia monitor.py per applicare i cambi.",
            "saved_at": datetime.now().isoformat(),
        }
    )


@app.get("/api/logs")
def get_logs():
    log_output, log_filename = read_last_log_lines()
    return jsonify({"log_output": log_output, "log_filename": log_filename})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
