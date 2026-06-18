import { renderDashboard } from './pages/dashboard.js'
import { renderSettings }  from './pages/settings.js'
import { renderTrips }     from './pages/trips.js'
import { renderAbout }     from './pages/about.js'
import { startBackend, getStatus } from './backend.js'

const PAGES = {
  dashboard: { label: 'Dashboard',    icon: iconHome(),      render: renderDashboard },
  settings:  { label: 'Settings',     icon: iconSettings(),  render: renderSettings  },
  trips:     { label: 'Trip History', icon: iconTrips(),     render: renderTrips     },
  about:     { label: 'About',        icon: iconInfo(),      render: renderAbout     },
}

let currentPage = 'dashboard'
export let botStatus = { bot_running: false, provider: '', model: '', username: '', vision: false }

function iconHome() { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/><path d="M9 21V12h6v9"/></svg>` }
function iconSettings() { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>` }
function iconTrips() { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2L16 11l3.5-3.5C21 6 21 4 21 4s-2 0-3.5 1.5L14 9 5.8 7.2c-.56-.12-1.14.1-1.48.54L3 9.5l5.5 2.5-1 2L5 15l1 1 1.5-1.5 2-1 2.5 5.5 1.76-1.32c.46-.34.67-.92.54-1.48z"/></svg>` }
function iconInfo() { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>` }

export function showToast(msg, type = '') {
  const c = document.getElementById('toast-root')
  const el = document.createElement('div')
  el.className = `toast ${type}`
  el.textContent = msg
  c.appendChild(el)
  setTimeout(() => el.remove(), 3500)
}

export async function refreshStatus() {
  const s = await getStatus()
  if (s) botStatus = s
  else botStatus = { bot_running: false, provider: '', model: '', username: '', vision: false }
  const dot = document.getElementById('nav-dot')
  if (dot) { dot.className = `nav-dot ${botStatus.bot_running ? 'on' : ''}` }
  return botStatus
}

export function navigate(page) {
  currentPage = page
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page))
  const main = document.getElementById('main')
  const ctx = { botStatus, navigate, showToast, refreshStatus }
  PAGES[page].render(main, ctx)
}

async function init() {
  const app = document.getElementById('app')
  app.innerHTML = `
    <div class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-wordmark">WanderOn</div>
        <div class="logo-tagline">AI Travel Guide</div>
      </div>
      <nav class="nav" id="nav">
        ${Object.entries(PAGES).map(([k, p]) => `
          <button class="nav-item ${k === 'dashboard' ? 'active' : ''}" data-page="${k}">
            ${p.icon} ${p.label}
            ${k === 'dashboard' ? '<span class="nav-dot" id="nav-dot"></span>' : ''}
          </button>`).join('')}
      </nav>
      <div class="sidebar-footer">WanderOn v2.0 · MIT</div>
    </div>
    <div class="main" id="main"></div>
    <div id="toast-root"></div>`

  document.getElementById('nav').addEventListener('click', e => {
    const b = e.target.closest('[data-page]')
    if (b) navigate(b.dataset.page)
  })

  await startBackend()
  await refreshStatus()
  setInterval(refreshStatus, 8000)
  navigate('dashboard')
}

init()
