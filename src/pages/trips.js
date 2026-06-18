import { getTrips, deleteTrip, clearTrips } from '../backend.js'

export async function renderTrips(container, { showToast }) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-title">Trip History</div>
      <div class="page-sub">All trips planned through WanderOn. Stored locally on your device only.</div>
    </div>
    <div class="trips-body" id="trips-body">
      <div style="color:var(--text3);font-size:13px">Loading…</div>
    </div>`

  const load = async () => {
    const trips = await getTrips()
    const body = container.querySelector('#trips-body')

    if (!trips.length) {
      body.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">🗺️</span>
          <div class="empty-title">No trips yet</div>
          <div class="empty-sub">Use /plan in your Telegram bot to start planning</div>
        </div>`
      return
    }

    body.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">
        <span style="font-size:13px;color:var(--text2)">${trips.length} trip${trips.length !== 1 ? 's' : ''} planned</span>
        <button class="btn btn-danger btn-sm" id="clear-btn">Clear all</button>
      </div>
      <div id="trip-list">
        ${trips.map(t => `
          <div class="trip-card" data-id="${t.id}">
            <div class="trip-icon">✈️</div>
            <div class="trip-info">
              <div class="trip-dest">${t.destination}</div>
              <div class="trip-meta">${t.dates} · ${t.members} traveller${t.members !== 1 ? 's' : ''} · ${t.budget} ${t.currency || 'INR'}</div>
              ${t.source_city ? `<div class="trip-meta" style="color:var(--text3)">From: ${t.source_city}</div>` : ''}
              <div class="trip-date">${new Date(t.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })}</div>
            </div>
            <div class="trip-actions">
              <button class="btn btn-secondary btn-sm view-btn" data-plan="${encodeURIComponent(t.full_plan || t.plan_summary)}" data-dest="${t.destination}">View</button>
              <button class="btn btn-danger btn-sm del-btn" data-id="${t.id}">✕</button>
            </div>
          </div>`).join('')}
      </div>`

    body.querySelector('#clear-btn').addEventListener('click', async () => {
      if (!confirm('Delete all trip history? This cannot be undone.')) return
      await clearTrips(); showToast('All trips cleared.', ''); load()
    })

    body.querySelectorAll('.del-btn').forEach(b => b.addEventListener('click', async e => {
      e.stopPropagation()
      await deleteTrip(b.dataset.id); showToast('Trip deleted.', ''); load()
    }))

    body.querySelectorAll('.view-btn').forEach(b => b.addEventListener('click', e => {
      e.stopPropagation()
      openModal(decodeURIComponent(b.dataset.plan), b.dataset.dest)
    }))
  }

  await load()
}

function openModal(plan, dest) {
  document.getElementById('_plan_modal')?.remove()
  const m = document.createElement('div')
  m.id = '_plan_modal'
  m.className = 'modal-backdrop'
  m.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Trip Plan — ${dest}</div>
        <button class="btn btn-secondary btn-sm" id="mc">Close</button>
      </div>
      <div class="modal-body">
        <pre class="modal-plan">${plan.replace(/</g,'&lt;')}</pre>
      </div>
    </div>`
  document.body.appendChild(m)
  m.querySelector('#mc').addEventListener('click', () => m.remove())
  m.addEventListener('click', e => { if (e.target === m) m.remove() })
}
