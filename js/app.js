// app.js — 主逻辑：数据加载、过滤、排序、渲染

const App = {
  programs: [],
  meta: null,
  filters: {
    univ: new Set(),
    major: 'all',
    type: 'all',
    status: 'all',
    query: '',
  },
  sort: 'deadline-asc',
  view: 'card', // card | list | timeline
};

// ========== 数据加载 ==========
async function loadData() {
  try {
    const [progResp, metaResp] = await Promise.all([
      fetch('data/programs.json'),
      fetch('data/meta.json'),
    ]);
    App.programs = (await progResp.json()).programs;
    App.meta = await metaResp.json();
  } catch (e) {
    console.error('数据加载失败，使用内嵌数据', e);
    App.programs = [];
    App.meta = null;
  }
}

// ========== 过滤 ==========
function applyFilters(programs, filters) {
  return programs.filter(p => {
    if (filters.univ.size > 0 && !filters.univ.has(p.university)) return false;
    if (filters.major !== 'all' && !p.majors.some(m => m === filters.major)) return false;
    if (filters.type !== 'all' && p.program_type !== filters.type) return false;
    if (filters.status !== 'all' && p.status !== filters.status) return false;
    if (filters.query) {
      const q = filters.query.toLowerCase();
      const text = [
        p.university, p.university_short, p.college, p.program_name,
        ...p.majors, ...p.tags || [], p.province, p.location,
      ].join(' ').toLowerCase();
      if (!text.includes(q)) return false;
    }
    return true;
  });
}

// ========== 排序 ==========
function sortPrograms(programs, sortKey) {
  const arr = [...programs];
  switch (sortKey) {
    case 'deadline-asc':
      return arr.sort((a, b) => {
        const da = a.application_deadline || '2099-12-31';
        const db = b.application_deadline || '2099-12-31';
        return da.localeCompare(db);
      });
    case 'deadline-desc':
      return arr.sort((a, b) => {
        const da = a.application_deadline || '2099-12-31';
        const db = b.application_deadline || '2099-12-31';
        return db.localeCompare(da);
      });
    case 'university':
      return arr.sort((a, b) => a.university.localeCompare(b.university, 'zh-CN'));
    case 'updated':
      return arr.sort((a, b) => (b.source?.crawled_at || '').localeCompare(a.source?.crawled_at || ''));
    default:
      return arr;
  }
}

// ========== 渲染 ==========
function render() {
  let filtered = applyFilters(App.programs, App.filters);
  filtered = sortPrograms(filtered, App.sort);

  const container = document.getElementById('cards-container');
  const countEl = document.getElementById('result-count');

  countEl.innerHTML = `共 <strong>${filtered.length}</strong> 条结果`;

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty"><div class="icon">📭</div><p>没有匹配的结果，试试调整筛选条件</p></div>`;
    container.className = 'content-inner';
    return;
  }

  if (App.view === 'timeline') {
    renderTimeline(filtered);
  } else {
    container.className = 'card-grid' + (App.view === 'list' ? ' list-view' : '');
    container.innerHTML = filtered.map(p => cardHtml(p)).join('');
  }

  // highlight active filter chips
  document.querySelectorAll('.filter-chip[data-filter]').forEach(chip => {
    const [key, val] = chip.dataset.filter.split(':');
    let active = false;
    if (key === 'major') active = App.filters.major === val;
    else if (key === 'type') active = App.filters.type === val;
    else if (key === 'status') active = App.filters.status === val;
    chip.classList.toggle('active', active);
    // special status colors
    if (key === 'status') {
      chip.classList.remove('status-active', 'status-soon', 'status-closed');
      if (active) {
        if (val === '报名中') chip.classList.add('status-active');
        else if (val === '即将截止') chip.classList.add('status-soon');
        else if (val === '已截止') chip.classList.add('status-closed');
      }
    }
  });
}

function cardHtml(p) {
  const stClass = STATUS_MAP[p.status] || 'pending';
  const typeClass = p.program_type === '夏令营' ? 'type-summer' : 'type-pre';
  const dl = daysLeft(p.application_deadline);
  const dlDisplay = p.application_deadline ? formatDate(p.application_deadline) : '待定';

  let dlClass = '';
  let daysHtml = '';
  if (p.status === '即将截止' && dl > 0 && dl <= 5) {
    dlClass = 'soon';
    daysHtml = `<span class="days-badge">还剩${dl}天</span>`;
  }
  if (p.status === '已截止') dlClass = 'past';

  const tags = (p.majors || []).map(m => `<span class="tag">${m}</span>`).join('');

  return `
<div class="card status-${stClass}" onclick="window.open('${escapeHtml(p.details_url)}','_blank')">
  <div class="card-header">
    <div class="uni-college">
      <span class="university">${escapeHtml(p.university)}</span>
      <span class="college">${escapeHtml(p.college)}</span>
      <span class="type-badge ${typeClass}">${p.program_type}</span>
    </div>
    <span class="status-badge ${stClass}">${p.status}</span>
  </div>

  <div class="program-name">${escapeHtml(p.program_name)}</div>

  <div class="meta-row">
    <span class="deadline ${dlClass}">📅 截止: ${dlDisplay} ${daysHtml}</span>
    <span>📍 ${escapeHtml(p.location || '')} | ${p.activity_mode || ''}</span>
    <span>🎓 ${(p.degree_types || []).join('/')}</span>
  </div>

  ${tags ? `<div class="tags">${tags}</div>` : ''}

  <div class="links" onclick="event.stopPropagation()">
    <a href="${escapeHtml(p.details_url)}" target="_blank" title="查看官方通知">查看详情</a>
    ${p.application_url ? `<a href="${escapeHtml(p.application_url)}" target="_blank" title="跳转报名系统">报名链接</a>` : ''}
    ${p.contact_email ? `<a href="mailto:${escapeHtml(p.contact_email)}">📧</a>` : ''}
  </div>
</div>`;
}

// ========== 时间线视图 ==========
function renderTimeline(programs) {
  const container = document.getElementById('cards-container');
  container.className = 'content-inner';

  // group by deadline date
  const groups = new Map();
  programs.forEach(p => {
    const dateKey = p.application_deadline ? p.application_deadline.slice(0, 10) : '待定';
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey).push(p);
  });

  let html = '<div class="timeline">';
  for (const [dateKey, items] of groups) {
    const dateLabel = dateKey === '待定' ? '待定' : formatDate(dateKey + 'T00:00:00+08:00');
    html += `<div class="timeline-date">📅 ${dateLabel}</div>`;
    items.forEach(p => {
      const stClass = STATUS_MAP[p.status] || 'pending';
      html += `<div class="timeline-item status-${stClass}">${cardHtml(p)}</div>`;
    });
  }
  html += '</div>';
  container.innerHTML = html;
}

// ========== UI 更新 ==========
function updateMeta() {
  if (!App.meta) return;
  const el = document.getElementById('update-time');
  if (el) el.textContent = relativeTime(App.meta.last_updated);
}

function setView(view) {
  App.view = view;
  document.querySelectorAll('.view-tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  render();
}

function setSort(sort) {
  App.sort = sort;
  render();
}

// ========== 事件绑定 ==========
function setupEvents() {
  // search
  const searchInput = document.getElementById('search-input');
  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      App.filters.query = searchInput.value.trim();
      render();
    }, 250);
  });

  // filter chips
  document.querySelectorAll('.filter-chip[data-filter]').forEach(chip => {
    chip.addEventListener('click', () => {
      const [key, val] = chip.dataset.filter.split(':');
      if (key === 'major') {
        App.filters.major = App.filters.major === val ? 'all' : val;
      } else if (key === 'type') {
        App.filters.type = App.filters.type === val ? 'all' : val;
      } else if (key === 'status') {
        App.filters.status = App.filters.status === val ? 'all' : val;
      }
      render();
    });
  });

  // view tabs
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', () => setView(tab.dataset.view));
  });

  // sort
  const sortSelect = document.getElementById('sort-select');
  sortSelect.addEventListener('change', () => setSort(sortSelect.value));

  // uni dropdown
  setupUniDropdown();
}

function setupUniDropdown() {
  const trigger = document.querySelector('.uni-trigger');
  const dropdown = document.querySelector('.uni-dropdown');
  const confirmBtn = dropdown.querySelector('.confirm');
  const clearBtn = dropdown.querySelector('.clear');

  trigger.addEventListener('click', e => {
    e.stopPropagation();
    dropdown.classList.toggle('show');
  });

  document.addEventListener('click', e => {
    if (!dropdown.contains(e.target) && e.target !== trigger) {
      dropdown.classList.remove('show');
    }
  });

  confirmBtn.addEventListener('click', () => {
    const checked = dropdown.querySelectorAll('input:checked');
    App.filters.univ = new Set(Array.from(checked).map(cb => cb.value));
    // update trigger text
    if (App.filters.univ.size === 0) {
      trigger.querySelector('.uni-label').textContent = '全部大学';
    } else {
      trigger.querySelector('.uni-label').textContent = `${App.filters.univ.size} 所学校`;
    }
    trigger.querySelector('.uni-count').textContent = App.filters.univ.size ? `(${App.filters.univ.size})` : '';
    dropdown.classList.remove('show');
    render();
  });

  clearBtn.addEventListener('click', () => {
    dropdown.querySelectorAll('input').forEach(cb => cb.checked = false);
    App.filters.univ = new Set();
    trigger.querySelector('.uni-label').textContent = '全部大学';
    trigger.querySelector('.uni-count').textContent = '';
    dropdown.classList.remove('show');
    render();
  });
}

// ========== 入口 ==========
async function init() {
  await loadData();
  updateMeta();
  setupEvents();
  render();
}

document.addEventListener('DOMContentLoaded', init);
