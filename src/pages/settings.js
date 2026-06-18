import { saveConfig, loadConfig, clearConfig, startBot, stopBot } from '../backend.js'

const PROVIDERS = [
  { id:'groq',       label:'Groq',           icon:'⚡', free:true,
    models:['llama-3.3-70b-versatile','llama-3.1-8b-instant','mixtral-8x7b-32768'],
    vision:['llama-3.2-90b-vision-preview','llama-3.2-11b-vision-preview'],
    keyLink:'https://console.groq.com/keys' },
  { id:'nvidia',     label:'NVIDIA Nemotron', icon:'🟩', free:true,
    models:['nvidia/llama-3.1-nemotron-70b-instruct','nvidia/llama-3.3-nemotron-super-49b-v1'],
    vision:['nvidia/neva-22b'],
    keyLink:'https://build.nvidia.com/' },
  { id:'openrouter', label:'OpenRouter',      icon:'🔀', free:true,
    models:['meta-llama/llama-3.3-70b-instruct:free','google/gemma-3-27b-it:free','deepseek/deepseek-r1:free'],
    vision:['qwen/qwen2.5-vl-32b-instruct:free'],
    keyLink:'https://openrouter.ai/keys' },
  { id:'gemini',     label:'Gemini',          icon:'✦',  free:true,
    models:['gemini-2.0-flash','gemini-1.5-pro','gemini-1.5-flash'],
    vision:['gemini-2.0-flash','gemini-1.5-pro'],
    keyLink:'https://aistudio.google.com/app/apikey' },
  { id:'openai',     label:'OpenAI',          icon:'◎',  free:false,
    models:['gpt-4o-mini','gpt-4o','gpt-3.5-turbo'],
    vision:['gpt-4o-mini','gpt-4o'],
    keyLink:'https://platform.openai.com/api-keys' },
  { id:'claude',     label:'Claude',          icon:'🔷', free:false,
    models:['claude-haiku-4-5-20251001','claude-sonnet-4-6'],
    vision:['claude-haiku-4-5-20251001','claude-sonnet-4-6'],
    keyLink:'https://console.anthropic.com/' },
  { id:'ollama',     label:'Ollama (local)',   icon:'🦙', free:true,
    models:['llama3.2','llama3.1','mistral','phi3'],
    vision:['llama3.2-vision'],
    keyLink:'http://localhost:11434' },
]

export async function renderSettings(container, { navigate, showToast, refreshStatus }) {
  const cfg = await loadConfig()
  let selProv = cfg.provider || 'groq'
  let selModel = cfg.model || PROVIDERS[0].models[0]

  const prov = () => PROVIDERS.find(p => p.id === selProv) || PROVIDERS[0]
  const isVision = (m) => prov().vision.includes(m)

  const render = () => {
    const p = prov()
    container.innerHTML = `
      <div class="page-header">
        <div class="page-title">Settings</div>
        <div class="page-sub">All API keys are saved in your OS keychain. Nothing is sent to any WanderOn server.</div>
      </div>
      <div class="settings-body">

        <div class="sec">
          <div class="sec-title">🤖 LLM Brain — choose your provider</div>
          <div class="provider-grid" id="pgrid">
            ${PROVIDERS.map(p => `
              <button class="prov-btn ${p.id === selProv ? 'sel' : ''}" data-p="${p.id}">
                <span class="prov-icon">${p.icon}</span>
                ${p.label}
                <span class="${p.free ? 'prov-free' : 'prov-paid'}">${p.free ? 'Free tier ✓' : 'Paid'}</span>
              </button>`).join('')}
          </div>
          <div class="form-group">
            <label>Model <span class="hint">📷 = supports image recognition</span></label>
            <select id="model-sel">
              ${p.models.concat(p.vision.filter(v => !p.models.includes(v))).map(m =>
                `<option value="${m}" ${m === selModel ? 'selected' : ''}>${m}${p.vision.includes(m) ? ' 📷' : ''}</option>`
              ).join('')}
            </select>
          </div>
          <div id="vision-note" class="vision-note ${isVision(selModel) ? 'vision-yes' : 'vision-no'}">
            ${isVision(selModel)
              ? '✓ This model supports image recognition. Send photos to your Telegram bot.'
              : '✗ Text-only model. Select a 📷 model above to enable photo recognition.'}
          </div>
          <div class="form-group">
            <label>
              API Key
              <span class="hint">— <button class="link-btn" id="get-key" type="button">Get ${p.free ? 'free ' : ''}key →</button></span>
            </label>
            <input type="password" id="llm-key"
              placeholder="${selProv === 'ollama' ? 'Not required for local Ollama' : 'Paste your API key here'}"
              value="${cfg.llmKey ? '••••••••' + cfg.llmKey.slice(-4) : ''}"
              ${selProv === 'ollama' ? 'disabled' : ''} />
            <div style="font-size:11.5px;color:var(--text3);margin-top:5px">
              Stored in ${keystoreName()}. Never transmitted to WanderOn — there is no central server.
            </div>
          </div>
        </div>

        <div class="sec">
          <div class="sec-title">📱 Telegram Bot</div>
          <div class="form-group">
            <label>Bot Token <span class="hint">— from @BotFather on Telegram</span></label>
            <input type="password" id="tg-tok"
              placeholder="1234567890:AAFxxxxxxxxx..."
              value="${cfg.tgToken ? '••••••' + cfg.tgToken.slice(-6) : ''}" />
          </div>
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 14px;font-size:12.5px;color:var(--text2)">
            <strong style="display:block;margin-bottom:5px;color:var(--text)">Create a Telegram bot in 60 seconds:</strong>
            1. Open Telegram → search <strong>@BotFather</strong><br>
            2. Send <code style="background:var(--primary-bg);color:var(--primary);padding:1px 5px;border-radius:3px">/newbot</code> and follow the prompts<br>
            3. Copy the token BotFather gives you → paste above
          </div>
        </div>

        <div class="sec">
          <div class="sec-title">🗺️ Data APIs <span style="font-weight:400;font-size:11px;color:var(--text3)">(optional — brings in real live data)</span></div>

          <div style="background:var(--primary-light);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 14px;font-size:12.5px;color:var(--text2);margin-bottom:14px">
            <strong style="color:var(--primary);display:block;margin-bottom:4px">Why these keys matter</strong>
            Without data APIs, the LLM uses its training knowledge — which can be outdated or imprecise for hotels and prices.
            With these keys, WanderOn fetches <strong>real, live hotel listings</strong> from Booking.com and Google Hotels, current weather, and accurate exchange rates.
          </div>

          <div class="form-group">
            <label>
              SerpAPI Key <span class="hint badge badge-success" style="font-size:10px">Recommended</span>
              <span class="hint">— <a href="https://serpapi.com/" target="_blank" class="link-btn">Get key (100 free/month) →</a></span>
            </label>
            <input type="password" id="serpapi-key" placeholder="Real Google Hotels data — actual prices & booking links"
              value="${cfg.serpapiKey ? '••••' + cfg.serpapiKey.slice(-4) : ''}" />
          </div>
          <div class="form-group">
            <label>OpenTripMap Key <span class="hint">— <a href="https://opentripmap.io/product" target="_blank" class="link-btn">Get free key →</a></span></label>
            <input type="password" id="otm-key" placeholder="Free — 5,000 req/day — real tourist attractions"
              value="${cfg.otmKey ? '••••' + cfg.otmKey.slice(-4) : ''}" />
          </div>
          <div class="form-group">
            <label>OpenWeatherMap Key <span class="hint">— <a href="https://openweathermap.org/appid" target="_blank" class="link-btn">Get free key →</a></span></label>
            <input type="password" id="owm-key" placeholder="Free — live weather forecasts for travel dates"
              value="${cfg.owmKey ? '••••' + cfg.owmKey.slice(-4) : ''}" />
          </div>
          <div class="form-group">
            <label>ExchangeRate-API Key <span class="hint">— <a href="https://www.exchangerate-api.com/" target="_blank" class="link-btn">Get free key →</a></span></label>
            <input type="password" id="er-key" placeholder="Free — live currency conversion for budgets"
              value="${cfg.erKey ? '••••' + cfg.erKey.slice(-4) : ''}" />
          </div>
        </div>

        <div class="flex-row">
          <button class="btn btn-primary" id="save-start">💾 Save & Start Bot</button>
          <button class="btn btn-secondary" id="save-only">Save Keys Only</button>
          <button class="btn btn-danger" id="clear-all">Clear All Keys</button>
        </div>
      </div>`

    container.querySelectorAll('.prov-btn').forEach(b => b.addEventListener('click', () => {
      selProv = b.dataset.p
      selModel = PROVIDERS.find(p => p.id === selProv)?.models[0] || ''
      render()
    }))

    container.querySelector('#model-sel').addEventListener('change', e => {
      selModel = e.target.value
      const note = container.querySelector('#vision-note')
      note.className = `vision-note ${isVision(selModel) ? 'vision-yes' : 'vision-no'}`
      note.textContent = isVision(selModel)
        ? '✓ This model supports image recognition. Send photos to your Telegram bot.'
        : '✗ Text-only model. Select a 📷 model above to enable photo recognition.'
    })

    container.querySelector('#get-key').addEventListener('click', () => window.open(prov().keyLink))

    async function gather() {
      const cur = await loadConfig()
      const llmRaw = container.querySelector('#llm-key').value
      const tgRaw  = container.querySelector('#tg-tok').value
      const otmRaw = container.querySelector('#otm-key').value
      const owmRaw = container.querySelector('#owm-key').value
      const erRaw  = container.querySelector('#er-key').value

      const serpapiRaw = container.querySelector('#serpapi-key').value
      const llmKey = llmRaw.includes('•') ? cur.llmKey : llmRaw.trim()
      const tgToken = tgRaw.includes('•') ? cur.tgToken : tgRaw.trim()
      const otmKey = otmRaw.includes('•') ? cur.otmKey : otmRaw.trim()
      const owmKey = owmRaw.includes('•') ? cur.owmKey : owmRaw.trim()
      const erKey  = erRaw.includes('•')  ? cur.erKey  : erRaw.trim()
      const serpapiKey = serpapiRaw.includes('•') ? cur.serpapiKey : serpapiRaw.trim()

      if (selProv !== 'ollama' && (!llmKey || llmKey.length < 8)) {
        showToast('Please enter a valid LLM API key.', 'error'); return null
      }
      if (!tgToken || !/^\d{6,12}:[A-Za-z0-9_-]{30,50}$/.test(tgToken)) {
        showToast('Telegram token format is invalid. Check @BotFather.', 'error'); return null
      }
      return { provider: selProv, model: selModel, tgToken, llmKey: llmKey || 'local', otmKey, owmKey, erKey, serpapiKey }
    }

    container.querySelector('#save-start').addEventListener('click', async () => {
      const btn = container.querySelector('#save-start')
      btn.textContent = 'Saving…'; btn.disabled = true
      const c = await gather()
      if (!c) { btn.textContent = '💾 Save & Start Bot'; btn.disabled = false; return }
      await saveConfig(c)
      try {
        const res = await startBot(c)
        if (res.success) { showToast('Bot started!', 'success'); navigate('dashboard') }
        else showToast(res.detail || res.message || 'Failed to start bot', 'error')
      } catch { showToast('Backend not reachable. Run: python backend/main.py', 'error') }
      btn.textContent = '💾 Save & Start Bot'; btn.disabled = false
    })

    container.querySelector('#save-only').addEventListener('click', async () => {
      const c = await gather(); if (!c) return
      await saveConfig(c); showToast('Keys saved securely.', 'success')
    })

    container.querySelector('#clear-all').addEventListener('click', async () => {
      if (!confirm('Clear all saved API keys? The bot will stop.')) return
      await stopBot(); await clearConfig()
      showToast('All keys cleared.', '')
      selProv = 'groq'; selModel = PROVIDERS[0].models[0]; render()
    })
  }

  render()
}

function keystoreName() {
  const ua = navigator.userAgent
  if (ua.includes('Win')) return 'Windows Credential Manager'
  if (ua.includes('Mac')) return 'macOS Keychain'
  return 'system keychain'
}
