/**
 * 总成核价计算报告（独立浅色页签）
 */

const STATUS_LABEL = {
    ok: '成功',
    partial: '部分成功',
    failed: '失败',
    skipped: '跳过',
    processing: '计算中',
    success: '成功',
};

const CARD_STATUS_CLASS = {
    ok: 'status-ok',
    partial: 'status-partial',
    failed: 'status-failed',
    skipped: 'status-skipped',
};

const state = {
    log: null,
    keyword: '',
    status: 'all',
    level: 'all',
    treeRoot: 'all',
};

function esc(value) {
    if (value == null || value === '') return '—';
    return String(value).replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
}

function token() {
    try {
        const session = JSON.parse(localStorage.getItem('brabus_user') || '{}');
        return session.token || '';
    } catch (_error) {
        return '';
    }
}

function logIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return parseInt(params.get('log_id') || '', 10);
}

async function loadLog(logId) {
    const auth = token();
    if (!auth) {
        throw new Error('未登录，请先打开主系统登录后再查看报告。');
    }
    const response = await fetch(`/api/costing/assembly-costs/calc/logs/${logId}`, {
        headers: {
            'X-Token': auth,
            Authorization: `Bearer ${auth}`,
        },
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
        throw new Error('登录已过期，请重新登录。');
    }
    if (!response.ok || payload.success === false) {
        throw new Error(payload.message || `加载失败（${response.status}）`);
    }
    return payload.data || {};
}

function formatWhen(value) {
    if (!value) return '—';
    return String(value).replace('T', ' ').slice(0, 19);
}

function uniqueLevels(cards) {
    return [...new Set(cards.map((card) => Number(card.level)).filter((n) => Number.isFinite(n)))].sort((a, b) => a - b);
}

function matches(card) {
    if (state.status !== 'all' && card.status !== state.status) return false;
    if (state.level !== 'all' && String(card.level) !== state.level) return false;
    if (state.treeRoot === 'yes' && !card.is_tree_root) return false;
    if (state.treeRoot === 'no' && card.is_tree_root) return false;
    const keyword = state.keyword.trim().toLowerCase();
    if (!keyword) return true;
    const hay = [
        card.part_number,
        card.part_name,
        card.message,
        card.object_kind,
        ...(card.missing_parts || []),
    ].join(' ').toLowerCase();
    return hay.includes(keyword);
}

function bindFilters(root) {
    const keyword = root.querySelector('#reportKeyword');
    keyword.value = state.keyword;
    keyword.addEventListener('input', () => {
        state.keyword = keyword.value;
        refreshRows(root);
    });
    root.querySelectorAll('[data-status]').forEach((btn) => {
        btn.addEventListener('click', () => {
            state.status = btn.dataset.status;
            refreshRows(root);
        });
    });
    const levelSelect = root.querySelector('#reportLevel');
    levelSelect.addEventListener('change', () => {
        state.level = levelSelect.value;
        refreshRows(root);
    });
    const treeSelect = root.querySelector('#reportTreeRoot');
    treeSelect.addEventListener('change', () => {
        state.treeRoot = treeSelect.value;
        refreshRows(root);
    });
}

function refreshRows(root) {
    const log = state.log;
    const cards = Array.isArray(log.cards) ? log.cards : [];
    const filtered = cards.filter(matches);
    root.querySelectorAll('[data-status]').forEach((btn) => {
        btn.classList.toggle('is-on', btn.dataset.status === state.status);
    });
    const count = root.querySelector('.count');
    if (count) count.textContent = `显示 ${filtered.length} / ${cards.length} 张卡`;
    const tableHost = root.querySelector('#reportTableHost');
    if (tableHost) tableHost.innerHTML = renderTable(filtered);
}

function render(root) {
    const log = state.log;
    const cards = Array.isArray(log.cards) ? log.cards : [];
    const filtered = cards.filter(matches);
    const period = `${log.year}-${String(log.month).padStart(2, '0')}`;
    const levels = uniqueLevels(cards);
    document.title = `总成核价计算报告 · ${period} · ${log.vehicle_model || ''}`;

    root.innerHTML = `
        <header class="report-head">
            <p>Assembly Costing Process Report</p>
            <h1>总成核价计算报告</h1>
        </header>
        <div class="meta">
            <div>范围 <strong>${esc(`${log.location} / ${log.vehicle_model} / ${log.bom_version}`)}</strong></div>
            <div>核价期 <strong>${esc(period)}</strong></div>
            <div>状态 <strong>${esc(STATUS_LABEL[log.status] || log.status)}</strong></div>
            <div>操作人 <strong>${esc(log.operator_name)}</strong></div>
            <div>开始 <strong>${esc(formatWhen(log.started_at))}</strong></div>
            <div>结束 <strong>${esc(formatWhen(log.finished_at))}</strong></div>
            <div>核价卡 <strong>${esc(log.subject_total ?? log.l0_total)}</strong></div>
            <div>成功 / 部分成功 / 失败 / 跳过
                <strong>${esc(log.ok_count)} / ${esc(log.partial_count)} / ${esc(log.failed_count)} / ${esc(log.skipped_approved_count)}</strong>
            </div>
        </div>
        <div class="filters">
            <input id="reportKeyword" type="search" placeholder="零件号、名称、说明">
            <button type="button" data-status="all">全部</button>
            <button type="button" data-status="ok">成功</button>
            <button type="button" data-status="partial">部分成功</button>
            <button type="button" data-status="failed">失败</button>
            <button type="button" data-status="skipped">跳过</button>
            <select id="reportLevel">
                <option value="all">全部层级</option>
                ${levels.map((level) => `<option value="${level}">L${level}</option>`).join('')}
            </select>
            <select id="reportTreeRoot">
                <option value="all">树根/非树根</option>
                <option value="yes">仅树根</option>
                <option value="no">非树根</option>
            </select>
            <span class="count">显示 ${filtered.length} / ${cards.length} 张卡</span>
        </div>
        <div class="body">
            ${log.message ? `<p class="summary">${esc(log.message)}</p>` : ''}
            ${log.detail_text ? `<pre class="narrative">${esc(log.detail_text)}</pre>` : ''}
            <div id="reportTableHost">${renderTable(filtered)}</div>
        </div>
    `;
    bindFilters(root);
    refreshRows(root);
}

function renderTable(cards) {
    if (!cards.length) {
        return '<p class="empty" style="padding:24px 0;">没有符合筛选的核价卡。</p>';
    }
    const rows = cards.map((card) => {
        const statusClass = CARD_STATUS_CLASS[card.status] || '';
        const missing = (card.missing_parts || []).join('；');
        return `
            <tr>
                <td>L${esc(card.level)}</td>
                <td>${card.is_tree_root ? '树根' : '—'}</td>
                <td>
                    <div style="font-weight:600;">${esc(card.part_number)}</div>
                    <div style="color:#78716c;font-size:12px;">${esc(card.part_name)}</div>
                </td>
                <td class="${statusClass}">${esc(STATUS_LABEL[card.status] || card.status)}</td>
                <td class="num">${esc(card.material_amount)}</td>
                <td class="num">${esc(card.welding_amount)}</td>
                <td class="num">${esc(card.should_cost)}</td>
                <td class="num">${esc(card.grand_total)}</td>
                <td class="num">${esc(card.missing_leaf_count)}</td>
                <td>${esc(card.message)}${missing ? `<div class="missing">${esc(missing)}</div>` : ''}</td>
            </tr>
        `;
    }).join('');
    return `
        <table>
            <thead>
                <tr>
                    <th>层级</th>
                    <th>树根</th>
                    <th>零件</th>
                    <th>状态</th>
                    <th style="text-align:right;">材料</th>
                    <th style="text-align:right;">焊接</th>
                    <th style="text-align:right;">应成本</th>
                    <th style="text-align:right;">总费用</th>
                    <th style="text-align:right;">缺价</th>
                    <th>说明</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

async function boot() {
    const root = document.getElementById('reportRoot');
    const logId = logIdFromUrl();
    if (!Number.isFinite(logId) || logId <= 0) {
        root.innerHTML = '<p class="error">缺少 log_id。</p>';
        return;
    }
    try {
        state.log = await loadLog(logId);
        render(root);
    } catch (error) {
        root.innerHTML = `<p class="error">${esc(error.message || '加载失败')}</p>`;
    }
}

boot();
