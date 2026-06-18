export function renderAbout(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title">About WanderOn</div>
      <div class="page-sub">Open-source AI travel guide. Your keys, your data, your machine.</div>
    </div>
    <div class="about-body">
      <div class="about-logo">WanderOn</div>
      <div class="about-tag">Your complete AI travel companion — plan everything like a local.</div>

      <div class="sec">
        <div class="sec-title">What WanderOn does</div>
        <ul class="feature-list">
          <li>Full day-wise itinerary with real place names, timing, meal spots</li>
          <li>Hotels within your budget — budget / mid / luxury with real names and nightly rates</li>
          <li>Complete cost breakdown — flights, stays, food, activities, SIM, tips per person</li>
          <li>Flights & airport routing — nearest airports both ends, fare ranges, booking links</li>
          <li>Cab & transport guide — which apps work locally (Uber/Grab/Bolt/Ola), estimated fares</li>
          <li>Local language cheatsheet — 15 essential phrases with pronunciation</li>
          <li>SIM card guide — best carriers, where to buy, cost, eSIM options</li>
          <li>Money & payment tips — cash vs card, ATM advice, tipping customs, price benchmarks</li>
          <li>Safety & scam alerts — top tourist scams, safe areas, emergency numbers, embassy</li>
          <li>Cultural etiquette — dress code, photography rules, local customs, taboos</li>
          <li>Food guide — must-try dishes, best restaurants, dietary info, food safety</li>
          <li>Visa checker — type needed, cost, processing time, documents required</li>
          <li>Packing list — tailored to destination, season, and trip type</li>
          <li>Health & vaccines — required shots, hospitals, water safety, pharmacies</li>
          <li>Image recognition — send a photo to identify landmarks, translate menus/signs</li>
          <li>Cost estimator — how much will any destination cost at different budget levels</li>
          <li>Photo-to-plan — snap a photo of a place and start a trip plan for it</li>
        </ul>
      </div>

      <div class="sec">
        <div class="sec-title">Privacy & security</div>
        <ul class="feature-list">
          <li>All API keys stored in OS keychain (Windows Credential Manager / macOS Keychain) — never in files</li>
          <li>Trip history saved in local SQLite at ~/.wanderon/ — never synced anywhere</li>
          <li>Financial data blocker — card numbers, UPI IDs, bank credentials blocked before reaching any LLM</li>
          <li>Rate limiting — 15 messages/minute per user, prevents abuse</li>
          <li>Fully open source — MIT license, audit the code anytime</li>
          <li>No telemetry, no analytics, no central account required</li>
          <li>Backend binds to 127.0.0.1 only — not accessible from the network</li>
        </ul>
      </div>

      <div class="sec">
        <div class="sec-title">Supported LLM providers</div>
        <ul class="feature-list">
          <li>Groq — Llama 3.3 70B (free, fast); Llama 3.2 Vision for photo recognition</li>
          <li>NVIDIA Nemotron — Llama-3.1/3.3 Nemotron via build.nvidia.com (free tier)</li>
          <li>OpenRouter — 100+ models including free ones; Qwen VL for vision</li>
          <li>Google Gemini — Gemini 2.0 Flash (free tier, supports vision)</li>
          <li>OpenAI — GPT-4o / GPT-4o mini (supports vision)</li>
          <li>Anthropic Claude — Haiku, Sonnet (supports vision)</li>
          <li>Ollama — fully local models, zero external API calls</li>
        </ul>
      </div>

      <div class="sec">
        <div class="sec-title">Tech stack</div>
        <ul class="feature-list">
          <li>Desktop: Tauri (Rust) + Vite + Vanilla JS — lightweight native window</li>
          <li>Backend: Python 3.12, FastAPI, python-telegram-bot 20.7</li>
          <li>Data: OpenTripMap, OpenWeatherMap, ExchangeRate-API, OpenFlights, Nominatim/OSM</li>
          <li>Storage: Local SQLite — no cloud database</li>
        </ul>
      </div>

      <div style="font-size:12px;color:var(--text3);margin-top:8px">WanderOn v2.0 · MIT License</div>
    </div>`
}
