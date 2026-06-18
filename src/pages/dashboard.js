import { loadConfig, startBot, stopBot } from '../backend.js'

const PROVIDER_NAMES = {
  groq: 'Groq', openai: 'OpenAI', claude: 'Claude',
  gemini: 'Google Gemini', openrouter: 'OpenRouter',
  nvidia: 'NVIDIA Nemotron', ollama: 'Ollama (local)'
}

export async function renderDashboard(container, { navigate, showToast, refreshStatus }) {
  const [status, config] = await Promise.all([refreshStatus(), loadConfig()])
  const hasKeys = !!(config.tgToken && config.llmKey)
  const provName = PROVIDER_NAMES[config.provider] || config.provider || '—'

  container.innerHTML = `
    <div class="dash-header">
      <div class="dash-title">Welcome to WanderOn ✈️</div>
      <div class="dash-subtitle">Your complete AI travel companion — itinerary, hotels, transport, culture, and more.</div>
    </div>
    <div class="dash-body">

      <div class="status-card ${status.bot_running ? 'running' : hasKeys ? '' : 'error'}" id="sc">
        <div class="status-icon">${status.bot_running ? '🟢' : hasKeys ? '⏸️' : '⚙️'}</div>
        <div class="status-text">
          <strong>${status.bot_running
            ? `Bot running · @${status.username || 'your-bot'}`
            : hasKeys ? 'Bot is paused' : 'Setup required'}</strong>
          <span>${status.bot_running
            ? `${provName} · ${status.model}`
            : hasKeys
              ? `${provName} configured — click Start to activate`
              : 'Go to Settings to add your Telegram token and LLM key'
          }</span>
        </div>
        <div class="status-actions">
          ${!hasKeys
            ? `<button class="btn btn-primary btn-sm" id="go-setup">Open Settings</button>`
            : status.bot_running
              ? `<button class="btn btn-danger btn-sm" id="stop-btn">Stop Bot</button>`
              : `<button class="btn btn-primary btn-sm" id="start-btn">▶ Start Bot</button>`}
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Bot Status</div>
          <div class="stat-value">
            <span class="badge ${status.bot_running ? 'badge-success' : 'badge-danger'}">
              ${status.bot_running ? '● Running' : '● Offline'}
            </span>
          </div>
          <div class="stat-sub">${status.bot_running ? 'Accepting messages' : 'Start bot to go live'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">LLM Provider</div>
          <div class="stat-value">
            <span class="badge ${config.provider ? 'badge-primary' : 'badge-neutral'}">${provName}</span>
          </div>
          <div class="stat-sub">${config.model || 'No model selected'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Telegram Bot</div>
          <div class="stat-value">
            <span class="badge ${config.tgToken ? 'badge-success' : 'badge-danger'}">
              ${config.tgToken ? 'Configured' : 'Not set'}
            </span>
          </div>
          <div class="stat-sub">${status.username ? `@${status.username}` : 'Set token in Settings'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Image Recognition</div>
          <div class="stat-value">
            <span class="badge ${status.vision ? 'badge-success' : 'badge-neutral'}">
              ${status.vision ? '📷 Enabled' : 'Text only'}
            </span>
          </div>
          <div class="stat-sub">${status.vision ? 'Send photos to your bot' : 'Pick a vision model in Settings'}</div>
        </div>
      </div>

      <div class="how-card">
        <div class="how-title">How it works</div>
        <div class="how-steps">
          ${[
            ['1', 'Add your API keys', 'Go to Settings, pick your LLM provider (Groq is free), paste your API keys. They are stored in your OS keychain — never on any server.'],
            ['2', 'Create a Telegram bot', 'Open Telegram → @BotFather → /newbot → copy the token → paste in Settings.'],
            ['3', 'Start the bot', 'Click Start Bot. Your Telegram bot goes live immediately.'],
            ['4', 'Open Telegram and type /plan', 'Tell WanderOn where to go, dates, group size, budget. Get a complete guide: itinerary, hotels, transport, language, safety, visa, and more.'],
            ['5', 'Use /guide, /cost, send photos', '/guide opens the city guide menu. /cost estimates trip costs. Send any photo — WanderOn identifies landmarks, reads menus, translates signs.'],
          ].map(([n, t, d]) => `
            <div class="how-step">
              <div class="step-num">${n}</div>
              <div class="step-body">
                <div class="step-title">${t}</div>
                <div class="step-desc">${d}</div>
              </div>
            </div>`).join('')}
        </div>
      </div>

      <div class="divider"></div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <div class="stat-card" style="flex:1;min-width:200px">
          <div class="stat-label">Telegram Commands</div>
          <div style="margin-top:8px;display:flex;flex-direction:column;gap:5px">
            ${['/plan','• Full trip planner','/cost','• Cost estimator','/guide','• City guide menu',
               '/history','• Past trips','/save','• Export current plan','/cancel','• Cancel session'].reduce((acc,v,i)=>
                i%2===0 ? [...acc,[v]] : [...acc.slice(0,-1),[...acc[acc.length-1],v]], [])
              .map(([cmd,desc])=>`<div style="display:flex;gap:8px;font-size:12.5px"><code style="background:var(--bg2);padding:1px 6px;border-radius:4px;color:var(--primary);font-size:12px">${cmd}</code><span style="color:var(--text2)">${desc}</span></div>`).join('')}
          </div>
        </div>
        <div class="stat-card" style="flex:1;min-width:200px">
          <div class="stat-label">What WanderOn plans for you</div>
          <div style="margin-top:8px;font-size:12.5px;color:var(--text2);line-height:2">
            ✈️ Flights & airports &nbsp; 🏨 Hotels within budget<br>
            🗓 Day-wise itinerary &nbsp; 💰 Full cost breakdown<br>
            🚕 Cabs & transport &nbsp; 🗣 Language phrases<br>
            📱 SIM card guide &nbsp; 💵 Money & tipping<br>
            🛡 Safety & scams &nbsp; 🎭 Cultural etiquette<br>
            🍜 Food guide &nbsp; 🧳 Packing list<br>
            📋 Visa info &nbsp; 💉 Health & vaccines
          </div>
        </div>
      </div>
    </div>`

  container.querySelector('#go-setup')?.addEventListener('click', () => navigate('settings'))

  container.querySelector('#start-btn')?.addEventListener('click', async () => {
    const btn = container.querySelector('#start-btn')
    btn.textContent = 'Starting…'; btn.disabled = true
    try {
      const cfg = await loadConfig()
      const res = await startBot(cfg)
      if (res.success) { showToast('Bot started!', 'success'); setTimeout(() => renderDashboard(container, { navigate, showToast, refreshStatus }), 1000) }
      else showToast((res.detail || res.message || 'Failed to start bot'), 'error')
    } catch { showToast('Backend not reachable. Is python main.py running?', 'error') }
    btn.textContent = '▶ Start Bot'; btn.disabled = false
  })

  container.querySelector('#stop-btn')?.addEventListener('click', async () => {
    await stopBot(); showToast('Bot stopped.', '')
    setTimeout(() => renderDashboard(container, { navigate, showToast, refreshStatus }), 600)
  })
}
