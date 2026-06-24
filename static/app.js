/* Hermes Mission Control — SPA Logic */
const API = '';

let state = {
  authenticated: false,
  activeTab: 'kanban',
  logsSource: 'gateway',
};

document.addEventListener('DOMContentLoaded', async () => {
  const resp = await fetch(`${API}/api/check-auth`);
  const data = await resp.json();
  if (data.authenticated) {
    state.authenticated = true;
    showDashboard();
  } else {
    showLogin();
  }

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = document.getElementById('password-input').value;
    if (!password) return;
    try {
      const resp = await fetch(`${API}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (resp.ok) {
        state.authenticated = true;
        showDashboard();
      } else {
        const err = await resp.json();
        document.getElementById('login-error').textContent = err.detail || 'Login failed';
        document.getElementById('login-error').classList.remove('hidden');
      }
    } catch (e) {
      document.getElementById('login-error').textContent = 'Connection error';
      document.getElementById('login-error').classList.remove('hidden');
    }
  });
});

function showLogin() {
  document.getElementById('login-screen').classList.remove('hidden');
  document.getElementById('dashboard').classList.add('hidden');
}

function showDashboard() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
  refreshAll();
  setInterval(refreshAll, 30000);
}

async function refreshAll() {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('spinning');

  await Promise.all([
    refreshStatus(),
    refreshTab(state.activeTab),
  ]).catch(() => {});

  setTimeout(() => btn.classList.remove('spinning'), 300);
}

// --- Status Cards + Version Badge ---
async function refreshStatus() {
  try {
    const resp = await fetch(`${API}/api/status`);
    const data = await resp.json();
    document.getElementById('stat-cron').textContent = data.cron_jobs ?? '—';
    document.getElementById('stat-profiles').textContent = data.profiles ?? '—';
    document.getElementById('stat-skills').textContent = data.skills ?? '—';
    document.getElementById('stat-sessions').textContent = data.sessions_24h ?? '—';

    const indicator = document.getElementById('gateway-indicator');
    if (data.gateway === 'running' || data.gateway_running) {
      indicator.textContent = '● Gateway Online';
      indicator.className = 'indicator online';
    } else {
      indicator.textContent = '● Gateway ' + (data.gateway || 'offline');
      indicator.className = 'indicator offline';
    }

    // Hermes version badge
    const verEl = document.getElementById('hermes-version');
    if (verEl && data.hermes) {
      const h = data.hermes;
      if (h.version) {
        if (h.up_to_date) {
          verEl.innerHTML = `v${esc(h.version)} <span class="badge badge-green">✓ Up to date</span>`;
          verEl.className = 'version-badge';
        } else if (h.up_to_date === false && h.latest_tag) {
          verEl.innerHTML = `v${esc(h.version)} <span class="badge badge-yellow">⬆ ${esc(h.latest_tag)}</span>`;
          verEl.className = 'version-badge';
        } else if (h.up_to_date === false) {
          verEl.innerHTML = `v${esc(h.version)} <span class="badge badge-yellow">⬆ Update avail.</span>`;
          verEl.className = 'version-badge';
        } else {
          verEl.textContent = `v${h.version}`;
          verEl.className = 'version-badge';
        }
      } else {
        verEl.textContent = 'Hermes —';
        verEl.className = 'version-badge';
      }
    }

    document.getElementById('last-updated').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch (_) {}
}

// --- Tab Switching ---
function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-content').forEach(tc => {
    tc.classList.toggle('hidden', tc.id !== `tab-${tab}`);
  });
  refreshTab(tab);
}

async function refreshTab(tab) {
  switch (tab) {
    case 'kanban': return renderKanban();
    case 'cron': return renderCron();
    case 'profiles': return renderProfiles();
    case 'skills': return renderSkills();
    case 'sessions': return renderSessions();
    case 'config': return renderConfig();
    case 'logs': return renderLogs();
  }
}

// ─── Kanban ────────────────────────────────────────────────────────────────
async function renderKanban() {
  const el = document.getElementById('tab-kanban');
  try {
    const resp = await fetch(`${API}/api/kanban`);
    const data = await resp.json();
    const columns = data.columns || [];
    const grouped = data.grouped || {};

    let html = '<div class="kanban-toolbar">';
    html += '<button class="kanban-add-btn" onclick="kanbanAddCard()">＋ Add Card</button>';
    html += '</div>';
    html += '<div class="kanban-board">';

    for (const col of columns) {
      const cards = grouped[col.id] || [];
      const colLabel = col.label || col.id;
      const colorClass = col.id === 'todo' ? 'kanban-col-todo'
        : col.id === 'in-progress' ? 'kanban-col-progress'
        : 'kanban-col-done';

      html += `<div class="kanban-column ${colorClass}">`;
      html += `<div class="kanban-col-header"><span class="kanban-col-title">${esc(colLabel)}</span><span class="kanban-col-count">${cards.length}</span></div>`;
      html += '<div class="kanban-cards">';

      if (cards.length === 0) {
        html += '<div class="kanban-empty">No cards</div>';
      } else {
        for (const card of cards) {
          const desc = card.description ? `<div class="kanban-card-desc">${esc(card.description)}</div>` : '';
          html += `
            <div class="kanban-card" data-id="${esc(card.id)}">
              <div class="kanban-card-title" ondblclick="kanbanEditTitle('${esc(card.id)}', this)">${esc(card.title)}</div>
              ${desc}
              <div class="kanban-card-actions">
                ${col.id !== 'todo' ? `<button class="kanban-btn" onclick="kanbanMove('${esc(card.id)}', 'left')">◀</button>` : '<span></span>'}
                ${col.id !== 'done' ? `<button class="kanban-btn" onclick="kanbanMove('${esc(card.id)}', 'right')">▶</button>` : '<span></span>'}
                <button class="kanban-btn kanban-btn-del" onclick="kanbanDelete('${esc(card.id)}')">✕</button>
              </div>
            </div>`;
        }
      }

      html += '</div></div>'; // col cards + column
    }

    html += '</div>'; // board
    el.innerHTML = html;
  } catch (_) {
    el.innerHTML = '<div class="empty-state"><p>Error loading kanban</p></div>';
  }
}

async function kanbanAddCard() {
  const title = prompt('Card title:');
  if (!title || !title.trim()) return;
  const col = prompt('Column (todo / in-progress / done):', 'todo') || 'todo';
  const desc = prompt('Description (optional):', '') || '';
  try {
    await fetch(`${API}/api/kanban`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title.trim(), column: col.trim(), description: desc.trim() }),
    });
    renderKanban();
  } catch (_) {}
}

async function kanbanEditTitle(cardId, el) {
  const current = el.textContent;
  const title = prompt('Edit title:', current);
  if (!title || !title.trim() || title.trim() === current) return;
  try {
    await fetch(`${API}/api/kanban/${cardId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title.trim() }),
    });
    renderKanban();
  } catch (_) {}
}

async function kanbanMove(cardId, dir) {
  try {
    const resp = await fetch(`${API}/api/kanban`);
    const data = await resp.json();
    const columns = data.columns || [];
    const card = (data.cards || []).find(c => c.id === cardId);
    if (!card) return;
    const colIdx = columns.findIndex(c => c.id === card.column);
    if (colIdx === -1) return;
    const targetIdx = dir === 'left' ? colIdx - 1 : colIdx + 1;
    if (targetIdx < 0 || targetIdx >= columns.length) return;
    await fetch(`${API}/api/kanban/${cardId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ column: columns[targetIdx].id }),
    });
    renderKanban();
  } catch (_) {}
}

async function kanbanDelete(cardId) {
  if (!confirm('Delete this card?')) return;
  try {
    await fetch(`${API}/api/kanban/${cardId}`, { method: 'DELETE' });
    renderKanban();
  } catch (_) {}
}

// ─── Cron ──────────────────────────────────────────────────────────────────
async function renderCron() {
  const el = document.getElementById('tab-cron');
  try {
    const resp = await fetch(`${API}/api/cron`);
    const data = await resp.json();
    if (!data.jobs || data.jobs.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">⏰</div><p>No cron jobs configured</p></div>';
      return;
    }
    let html = '<div class="cron-grid">';
    for (const j of data.jobs) {
      const stateColor = j.state === 'scheduled' ? 'badge-green' : j.state === 'paused' ? 'badge-yellow' : 'badge-blue';
      const lastStatus = j.last_status === 'ok' ? 'badge-green' : 'badge-red';
      html += `
        <div class="cron-card">
          <div class="cron-card-header">
            <h3>${esc(j.name || 'Unnamed')}</h3>
            <span class="badge ${stateColor}">${j.state || '?'}</span>
          </div>
          <div class="cron-card-body">
            <span class="key">Schedule:</span><span>${j.schedule_display || esc(j.schedule?.expr || '?')}</span>
            <span class="key">Status:</span><span><span class="badge ${lastStatus}">${j.last_status || 'never'}</span></span>
            <span class="key">Last run:</span><span>${fmtTime(j.last_run_at)}</span>
            <span class="key">Next run:</span><span>${fmtTime(j.next_run_at)}</span>
            <span class="key">Runs:</span><span>${j.repeat?.completed ?? 0}</span>
            <span class="key">Deliver:</span><span>${j.deliver || 'origin'}</span>
            ${j.prompt_preview ? `<span class="key">Prompt:</span><span class="text-muted">${esc(j.prompt_preview)}</span>` : ''}
          </div>
        </div>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><p>Error loading cron jobs</p></div>`;
  }
}

// ─── Profiles ──────────────────────────────────────────────────────────────
async function renderProfiles() {
  const el = document.getElementById('tab-profiles');
  try {
    const resp = await fetch(`${API}/api/profiles`);
    const data = await resp.json();
    if (!data.profiles || data.profiles.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">👤</div><p>No profiles configured</p></div>';
      return;
    }
    let html = '<div class="data-panel">';
    for (const p of data.profiles) {
      const gwState = p.gateway_running ? 'badge-green' : 'badge-yellow';
      const gwText = p.gateway_running ? 'running' : (p.gateway_status || 'inactive');
      html += `
        <div class="data-item">
          <div class="data-label">${esc(p.name)}</div>
          <div class="data-value">
            <span class="badge ${gwState}">${gwText}</span>
            ${p.model ? `<span style="margin-left:0.5rem;color:var(--text-muted)">${esc(p.model)}</span>` : ''}
            ${p.provider ? `<span style="color:var(--text-muted)">@${esc(p.provider)}</span>` : ''}
          </div>
        </div>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (_) {
    el.innerHTML = '<div class="empty-state"><p>Error loading profiles</p></div>';
  }
}

// ─── Skills ────────────────────────────────────────────────────────────────
async function renderSkills() {
  const el = document.getElementById('tab-skills');
  try {
    const resp = await fetch(`${API}/api/skills`);
    const data = await resp.json();
    if (!data.skills || data.skills.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">🧠</div><p>No skills installed</p></div>';
      return;
    }
    let html = `<p style="margin-bottom:0.75rem;color:var(--text-muted)">${data.total} skills in ${data.categories?.length || 0} categories</p>`;
    html += '<div class="skills-cloud">';
    for (const s of data.skills) {
      const cat = s.category ? `<span class="cat">${esc(s.category)}</span>` : '';
      html += `<span class="skill-chip">${cat}${esc(s.name)}</span>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (_) {
    el.innerHTML = '<div class="empty-state"><p>Error loading skills</p></div>';
  }
}

// ─── Sessions ──────────────────────────────────────────────────────────────
async function renderSessions() {
  const el = document.getElementById('tab-sessions');
  try {
    const resp = await fetch(`${API}/api/sessions?limit=20`);
    const data = await resp.json();
    if (!data.sessions || data.sessions.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">💬</div><p>No recent sessions</p></div>';
      return;
    }
    let html = '<div class="data-panel">';
    for (const s of data.sessions) {
      html += `
        <div class="session-row">
          <div>
            <div class="session-title">${esc(s.title || 'Untitled')}</div>
            <div class="session-meta">
              <span>${s.platform || s.source || 'cli'}</span>
              <span>${s.message_count || 0} messages</span>
            </div>
          </div>
          <div style="font-size:0.8rem;color:var(--text-muted);text-align:right">
            <div>${fmtTime(s.started_at)}</div>
          </div>
        </div>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (_) {
    el.innerHTML = '<div class="empty-state"><p>Error loading sessions</p></div>';
  }
}

// ─── Config ────────────────────────────────────────────────────────────────
async function renderConfig() {
  const el = document.getElementById('tab-config');
  try {
    const resp = await fetch(`${API}/api/config`);
    const data = await resp.json();
    if (!data.config) {
      el.innerHTML = '<div class="empty-state"><p>Config not available</p></div>';
      return;
    }
    const html = '<div class="data-panel config-tree">' + renderConfigTree(data.config) + '</div>';
    el.innerHTML = html;
  } catch (_) {
    el.innerHTML = '<div class="empty-state"><p>Error loading config</p></div>';
  }
}

function renderConfigTree(obj, depth = 0) {
  if (obj === null || obj === undefined) return '<span style="color:var(--text-muted)">null</span>';
  if (typeof obj === 'string') return `<span style="color:#a5d6ff">"${esc(obj)}"</span>`;
  if (typeof obj === 'number' || typeof obj === 'boolean') return `<span style="color:#79c0ff">${obj}</span>`;
  if (Array.isArray(obj)) {
    if (obj.length === 0) return '<span style="color:var(--text-muted)">[]</span>';
    return '<div style="margin-left:1.5rem">' + obj.map(v => '<div>· ' + renderConfigTree(v, depth + 1) + '</div>').join('') + '</div>';
  }
  if (typeof obj === 'object') {
    const keys = Object.keys(obj);
    if (keys.length === 0) return '<span style="color:var(--text-muted)">{}</span>';
    return '<div style="margin-left:1.5rem">' +
      keys.map(k => `<div><span class="config-key">${esc(k)}</span>: ${renderConfigTree(obj[k], depth + 1)}</div>`).join('') +
      '</div>';
  }
  return String(obj);
}

// ─── Logs ──────────────────────────────────────────────────────────────────
async function renderLogs(source) {
  const el = document.getElementById('tab-logs');
  if (source) state.logsSource = source;

  const logTabs = `
    <div class="log-tabs">
      <button class="log-tab ${state.logsSource === 'gateway' ? 'active' : ''}" onclick="renderLogs('gateway')">Gateway</button>
      <button class="log-tab ${state.logsSource === 'agent' ? 'active' : ''}" onclick="renderLogs('agent')">Agent</button>
      <button class="log-tab ${state.logsSource === 'errors' ? 'active' : ''}" onclick="renderLogs('errors')">Errors</button>
    </div>`;

  try {
    const resp = await fetch(`${API}/api/logs?lines=60`);
    const data = await resp.json();
    const lines = data[state.logsSource] || [];
    if (lines.length === 0) {
      el.innerHTML = logTabs + '<div class="empty-state"><p>No log entries</p></div>';
      return;
    }
    const joined = esc(lines.join('\n'));
    const size = lines.length;
    el.innerHTML = logTabs + `<div class="log-viewer">${joined}</div>
      <p style="font-size:0.8rem;color:var(--text-muted);margin-top:0.5rem">${size} lines · last 60 shown</p>`;
    const viewer = el.querySelector('.log-viewer');
    if (viewer) viewer.scrollTop = viewer.scrollHeight;
  } catch (_) {
    el.innerHTML = logTabs + '<div class="empty-state"><p>Error loading logs</p></div>';
  }
}

// ─── Logout ────────────────────────────────────────────────────────────────
async function logout() {
  await fetch(`${API}/api/logout`);
  state.authenticated = false;
  showLogin();
}

// ─── Utils ─────────────────────────────────────────────────────────────────
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return iso || '—'; }
}
