#  WanderOn — AI Travel Planner

**WanderOn** is an open-source desktop application that runs a personal AI travel planning bot on your Telegram. Just tell it your destination, dates, group size, and budget — it generates a complete trip plan with itinerary, transport, stays, and budget breakdown.

> **Your keys. Your data. Your machine.** No central server. No data collection. API keys stored in your OS keychain.

---

##  What's included

```
wanderon/
├── backend/              ← Python FastAPI server + Telegram bot
│   ├── main.py           ← FastAPI entry point
│   ├── bot.py            ← Telegram bot (conversation state machine)
│   ├── planner.py        ← Travel plan orchestrator
│   ├── llm.py            ← Multi-provider LLM client
│   ├── travel_data.py    ← OpenTripMap, weather, airports, currency
│   ├── db.py             ← Local SQLite session + trip history
│   └── requirements.txt
├── src/                  ← Frontend (Vite + vanilla JS)
│   ├── main.js           ← App shell + router
│   ├── style.css         ← Design system
│   ├── backend.js        ← Tauri keychain + API client
│   └── pages/
│       ├── dashboard.js
│       ├── settings.js
│       ├── trips.js
│       └── about.js
├── src-tauri/            ← Rust/Tauri desktop wrapper
│   ├── src/main.rs       ← Keychain commands + system tray
│   ├── Cargo.toml
│   └── tauri.conf.json
├── setup.py              ← One-time setup script
├── run_dev.py            ← Dev mode runner (backend only)
├── run_backend_only.sh   ← Quick backend start (Linux/Mac)
└── run_backend_only.bat  ← Quick backend start (Windows)
```

---

##  Quick Start (Two ways)

### Way 1 — Browser mode (easiest, no Rust needed)

Good for development and testing. Uses the browser instead of a native window.

**Prerequisites:** Python 3.10+, Node.js 18+

```bash
# 1. Clone the repo
git clone https://github.com/your-username/wanderon
cd wanderon

# 2. Run setup (installs Python deps)
python setup.py

# 3. Install Node deps
npm install

# 4. Terminal 1 — Start backend
python run_dev.py

# 5. Terminal 2 — Start frontend
npm run dev

# 6. Open http://localhost:1420 in your browser
```

---

### Way 2 — Full desktop app (Tauri)

Builds the actual `.exe` / `.dmg` / `.AppImage` native app.

**Prerequisites:** Python 3.10+, Node.js 18+, Rust (https://rustup.rs)

**Linux only — install system packages first:**
```bash
sudo apt-get update
sudo apt-get install -y \
  libwebkit2gtk-4.0-dev libssl-dev libgtk-3-dev \
  libayatana-appindicator3-dev librsvg2-dev libsecret-1-dev
```

**All platforms:**
```bash
# 1. Clone and enter
git clone https://github.com/your-username/wanderon
cd wanderon

# 2. Setup
python setup.py
npm install

# 3. Run in dev mode (hot reload)
npm run tauri:dev

# OR build for production
npm run tauri:build
# Output: src-tauri/target/release/bundle/
```

---

##  First-time Configuration (in the app)

Once the app opens:

1. **Go to Settings**
2. **Pick your LLM provider** — Groq is recommended (free, fast):
   - Groq → https://console.groq.com/keys
   - OpenRouter → https://openrouter.ai/keys
   - Gemini → https://aistudio.google.com/app/apikey
   - OpenAI → https://platform.openai.com/api-keys
   - Claude → https://console.anthropic.com/
   - Ollama → install locally, no key needed
3. **Create a Telegram bot:**
   - Open Telegram → search `@BotFather`
   - Send `/newbot`, follow prompts
   - Copy the token it gives you
4. **Paste your token and LLM key** into Settings
5. **(Optional) Add free data API keys** for richer results:
   - OpenTripMap (tourist spots): https://opentripmap.io/product
   - OpenWeatherMap (forecasts): https://openweathermap.org/appid
   - ExchangeRate-API (currency): https://www.exchangerate-api.com/
6. **Click "Save & Start Bot"**

Your bot is now live. Open Telegram and send `/plan` to start!

---

##  Telegram Bot Commands

| Command    | What it does |
|-----------|--------------|
| `/plan`   | Start planning a new trip |
| `/cancel` | Cancel current session |
| `/history`| View your 5 most recent trips |
| `/help`   | Show all commands |

**Example conversation:**
```
You:  /plan
Bot:  Where do you want to go?
You:  Paris
Bot:  Where are you travelling from?
You:  Mumbai
Bot:  When are you planning to travel?
You:  15 Dec to 22 Dec
Bot:  [Shows member count buttons]
You:  [Taps "2"]
Bot:  What is your total budget?
You:  80000 INR
Bot:  🔍 Planning your trip to Paris...
Bot:  [Full itinerary, transport, stays, budget breakdown]
You:  What's the best area to stay near the Eiffel Tower?
Bot:  [Follow-up answer based on the plan]
```

---

##  Privacy & Security

| What | How it's handled |
|------|-----------------|
| API keys | Stored in OS keychain (Windows Credential Manager / macOS Keychain / libsecret). Never in files or servers. |
| Trip history | Local SQLite at `~/.wanderon/trips.db`. Never synced anywhere. |
| Financial data | Card numbers, UPI IDs, bank credentials are blocked at input before reaching the LLM. |
| Telegram chats | Your bot runs on your own token. WanderOn never sees your messages. |
| Telemetry | None. Zero. |
| Source code | Fully open source. Audit it anytime. |

---

##  Supported LLM Providers

| Provider   | Free tier | Best model for travel |
|-----------|-----------|----------------------|
| Groq       | ✅ Yes    | llama-3.3-70b-versatile |
| OpenRouter | ✅ Yes    | meta-llama/llama-3.3-70b-instruct:free |
| Gemini     | ✅ Yes    | gemini-2.0-flash |
| OpenAI     | ❌ Paid   | gpt-4o-mini |
| Claude     | ❌ Paid   | claude-haiku-4-5-20251001 |
| Ollama     | ✅ Local  | llama3.2 |

---

##  Data & Storage

All data lives at `~/.wanderon/`:
```
~/.wanderon/
└── trips.db      ← SQLite: trip history + sessions
```

API keys: stored in system keychain, never on disk in plaintext.

To wipe all data: delete `~/.wanderon/` and clear keys in Settings → "Clear All Keys".

---

##  Building for Distribution

GitHub Actions (`.github/workflows/build.yml`) automatically builds installers for all platforms when you push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Outputs:
- Windows: `WanderOn_1.0.0_x64.msi` + `WanderOn_1.0.0_x64-setup.exe`
- macOS: `WanderOn_1.0.0_x64.dmg`
- Linux: `wanderon_1.0.0_amd64.AppImage` + `.deb`

---

##  Troubleshooting

**Backend won't start:**
```bash
cd backend
pip install -r requirements.txt
python main.py
# Should print: [WanderOn] ... backend started on http://127.0.0.1:7291
```

**Bot not responding on Telegram:**
- Check Settings → bot status should show green
- Verify your Telegram token is correct (no extra spaces)
- Try `/start` in the bot chat first

**LLM errors:**
- Double-check your API key in Settings (re-paste it)
- For Groq/OpenRouter: verify your free tier quota hasn't reset
- For Ollama: make sure `ollama serve` is running locally

**"Backend not reachable" error in UI:**
- The Python backend must be running separately in dev mode
- Run `python run_dev.py` in a terminal and keep it open

**Linux: keychain errors:**
```bash
sudo apt-get install libsecret-1-dev gnome-keyring
# Then restart and try again
```

---

##  License

MIT — free to use, modify, and distribute.

---

##  Built with

- [Tauri](https://tauri.app) — lightweight desktop framework
- [python-telegram-bot](https://python-telegram-bot.org) — Telegram API
- [FastAPI](https://fastapi.tiangolo.com) — backend API server
- [OpenTripMap](https://opentripmap.io) — tourist attractions data
- [OpenFlights](https://openflights.org/data) — airport data
- [Nominatim/OSM](https://nominatim.openstreetmap.org) — geocoding
