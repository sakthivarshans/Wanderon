/**
 * Frontend communication gateway and local persistence config keys.
 */
const API = 'http://127.0.0.1:7291'
const SVC = 'wanderon'

/**
 * Detects if the current environment is running inside the Tauri desktop wrapper.
 * @returns {boolean} True if running under Tauri, False otherwise.
 */
function isTauri() { return !!(window.__TAURI__ || window.__TAURI_IPC__) }

/**
 * Saves a key-value configuration pair securely in Tauri keychain or falls back to session storage.
 * @param {string} key Configuration key identifier.
 * @param {string} value Raw token or key value.
 */
async function kSave(key, value) {
  if (!isTauri()) { sessionStorage.setItem(`wo_${key}`, value || ''); return }
  await window.__TAURI__.tauri.invoke('save_key', { service: SVC, key, value })
}

/**
 * Loads a key-value configuration pair from the Tauri keychain or fallback storage.
 * @param {string} key Configuration key identifier.
 * @returns {Promise<string>} Saved config value.
 */
async function kLoad(key) {
  if (!isTauri()) { return sessionStorage.getItem(`wo_${key}`) || '' }
  try { return await window.__TAURI__.tauri.invoke('load_key', { service: SVC, key }) } catch { return '' }
}

/**
 * Deletes a key-value configuration pair from the Tauri keychain or fallback storage.
 * @param {string} key Configuration key identifier.
 */
async function kDel(key) {
  if (!isTauri()) { sessionStorage.removeItem(`wo_${key}`); return }
  try { await window.__TAURI__.tauri.invoke('delete_key', { service: SVC, key }) } catch {}
}

const KEYS = ['provider','model','tg_token','llm_key','otm_key','owm_key','er_key','serpapi_key']

/**
 * Securely persists the entire LLM and Telegram configuration object.
 * @param {object} cfg Application config payload.
 */
export async function saveConfig(cfg) {
  await kSave('provider',    cfg.provider)
  await kSave('model',       cfg.model)
  await kSave('tg_token',    cfg.tgToken)
  await kSave('llm_key',     cfg.llmKey)
  await kSave('otm_key',     cfg.otmKey    || '')
  await kSave('owm_key',     cfg.owmKey    || '')
  await kSave('er_key',      cfg.erKey     || '')
  await kSave('serpapi_key', cfg.serpapiKey || '')
}

/**
 * Loads the application configuration object from keychain storage.
 * @returns {Promise<object>} Loaded configuration attributes.
 */
export async function loadConfig() {
  const [provider, model, tgToken, llmKey, otmKey, owmKey, erKey, serpapiKey] = await Promise.all(KEYS.map(k => kLoad(k)))
  return { provider, model, tgToken, llmKey, otmKey, owmKey, erKey, serpapiKey }
}

/**
 * Clears all configuration elements from secure system keychain.
 */
export async function clearConfig() {
  await Promise.all(KEYS.map(k => kDel(k)))
}

/**
 * Queries the active backend connection status and details.
 * @returns {Promise<object|null>} Status payload or null.
 */
export async function getStatus() {
  try {
    const r = await fetch(`${API}/status`, { signal: AbortSignal.timeout(3000) })
    return r.ok ? r.json() : null
  } catch { return null }
}

/**
 * Sends a command to the backend to initialize and start the Telegram bot client.
 * @param {object} cfg Loaded application config object.
 * @returns {Promise<object>} Response payload containing success state.
 */
export async function startBot(cfg) {
  const r = await fetch(`${API}/configure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      telegram_token: cfg.tgToken, llm_provider: cfg.provider,
      llm_api_key: cfg.llmKey || 'local', llm_model: cfg.model,
      otm_key: cfg.otmKey || '', owm_key: cfg.owmKey || '', er_key: cfg.erKey || '',
      serpapi_key: cfg.serpapiKey || '',
    }),
  })
  return r.json()
}

/**
 * Stops the Telegram bot execution process on the backend.
 * @returns {Promise<object>} Stop operation response.
 */
export async function stopBot() {
  try { const r = await fetch(`${API}/stop`, { method: 'POST' }); return r.json() } catch { return { success: false } }
}

/**
 * Fetches the recent travel plans stored in the local database.
 * @returns {Promise<Array>} List of planned trips.
 */
export async function getTrips() {
  try { const r = await fetch(`${API}/trips`); return r.ok ? r.json() : [] } catch { return [] }
}

/**
 * Removes a specific trip from local storage.
 * @param {number} id Target trip record ID.
 * @returns {Promise<boolean>} Success state.
 */
export async function deleteTrip(id) {
  try { await fetch(`${API}/trips/${id}`, { method: 'DELETE' }); return true } catch { return false }
}

/**
 * Clears all trip history records from local SQLite tables.
 * @returns {Promise<boolean>} Success state.
 */
export async function clearTrips() {
  try { await fetch(`${API}/trips`, { method: 'DELETE' }); return true } catch { return false }
}
/**
 * Attempts to contact and verify the local python server health.
 * Performs automatic bot initialization if credentials exist.
 */
export async function startBackend() {
  for (let i = 0; i < 20; i++) {
    try {
      const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(800) })
      if (r.ok) {
        const cfg = await loadConfig()
        if (cfg.tgToken && cfg.llmKey) await startBot(cfg)
        return
      }
    } catch {}
    await new Promise(r => setTimeout(r, 500))
  }
  console.warn('Backend did not respond within 10s — run: python backend/main.py')
}
export { API }
