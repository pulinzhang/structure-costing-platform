/**
 * 冲压零件列表页脚本
 *
 * 依赖（由模板注入）：
 *   - PARTS_API          { LIST, DETAIL(id), DELETE(id) }
 *   - PARTS_PAGE_SIZE    每页大小
 *   - SEARCH_DEBOUNCE_MS 搜索防抖毫秒
 *
 * DOM 节点：
 *   #searchInput         搜索输入框
 *   #vehicleModelFilter  车型筛选
 *   #versionFilter       版本筛选
 *   #totalCount          总数展示
 *   #partsTableBody      表格 tbody
 *   #pagination          分页 ul
 *   #partDetailModal     详情 Modal
 *   #partDetailContent   详情内容容器
 */

// ===== 工具函数 =====

/** 数字安全格式化：null/undefined/NaN → '-' */
const fmtNumber = (value, digits) => {
    if (value == null || Number.isNaN(value)) return '-';
    return Number(value).toFixed(digits);
};

/** HTML 转义：避免 XSS */
const esc = (value) => {
    if (value == null) return '-';
    return String(value).replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
};

// ===== DOM 引用 =====

const dom = {
    searchInput:        document.getElementById('searchInput'),
    vehicleModelFilter: document.getElementById('vehicleModelFilter'),
    versionFilter:      document.getElementById('versionFilter'),
    totalCount:         document.getElementById('totalCount'),
    partsTableBody:     document.getElementById('partsTableBody'),
    pagination:         document.getElementById('pagination'),
    partDetailContent:  document.getElementById('partDetailContent'),
    partDetailModalEl:  document.getElementById('partDetailModal'),
};

// ===== 状态 =====

const state = {
    currentPage: 1,
    isLoading: false,
    searchTimer: null,
};

// ===== 渲染：表格行 =====

/** 空状态 HTML（与服务端 empty_state 宏一致） */
function renderEmptyRow(message = '暂无零件数据', hint = '请联系管理员导入工艺文件', colspan = 9) {
    return `
        <tr><td colspan="${colspan}">
            <div class="empty-state py-5">
                <i class="bi bi-inbox"></i>
                <h5>${esc(message)}</h5>
                <p class="text-muted">${esc(hint)}</p>
            </div>
        </td></tr>
    `;
}

/** 渲染单条零件行 */
function renderPartRow(part) {
    return `
        <tr>
            <td><strong>${esc(part.part_number)}</strong></td>
            <td>${esc(part.part_name)}</td>
            <td><span class="badge bg-primary">${esc(part.vehicle_model)}</span></td>
            <td><span class="badge bg-secondary">${esc(part.version)}</span></td>
            <td>${esc(part.material)}</td>
            <td>${fmtNumber(part.thickness, 2)}</td>
            <td>${fmtNumber(part.part_weight, 3)}</td>
            <td><span class="badge bg-info">${part.process_count ?? 0}</span></td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary" data-action="detail" data-id="${part.id}">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${part.id}">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `;
}

function renderParts(parts) {
    if (!parts || parts.length === 0) {
        dom.partsTableBody.innerHTML = renderEmptyRow();
        return;
    }
    dom.partsTableBody.innerHTML = parts.map(renderPartRow).join('');
}

// ===== 渲染：分页 =====

function renderPagination(pageInfo) {
    const { total, page, total_pages, has_next, has_prev } = pageInfo;
    dom.totalCount.textContent = `共 ${total} 个零件，第 ${page}/${total_pages || 1} 页`;

    if (!total_pages || total_pages <= 1) {
        dom.pagination.innerHTML = '';
        return;
    }

    // 窗口分页：最多 ±2 页 + 首末页
    const window = 2;
    const pages = new Set([1, total_pages]);
    for (let i = Math.max(1, page - window); i <= Math.min(total_pages, page + window); i++) {
        pages.add(i);
    }
    const sortedPages = Array.from(pages).sort((a, b) => a - b);

    let html = `
        <li class="page-item ${has_prev ? '' : 'disabled'}">
            <a class="page-link" href="#" data-page="${page - 1}" aria-label="上一页">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
    `;

    let lastPage = 0;
    for (const p of sortedPages) {
        if (lastPage && p - lastPage > 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `
            <li class="page-item ${p === page ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${p}">${p}</a>
            </li>
        `;
        lastPage = p;
    }

    html += `
        <li class="page-item ${has_next ? '' : 'disabled'}">
            <a class="page-link" href="#" data-page="${page + 1}" aria-label="下一页">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;

    dom.pagination.innerHTML = html;
}

// ===== 数据加载 =====

async function loadParts(page = 1) {
    if (state.isLoading) return;
    state.isLoading = true;
    state.currentPage = page;

    const params = {
        skip: (page - 1) * PARTS_PAGE_SIZE,
        limit: PARTS_PAGE_SIZE,
    };

    const partNumber = dom.searchInput.value.trim();
    const vehicleModel = dom.vehicleModelFilter.value;
    const version = dom.versionFilter.value;
    if (partNumber) params.part_number = partNumber;
    if (vehicleModel) params.vehicle_model = vehicleModel;
    if (version) params.version = version;

    try {
        const result = await HttpClient.get(PARTS_API.LIST, { params });
        const pageInfo = result.data || {};
        renderParts(pageInfo.list || []);
        renderPagination(pageInfo);
    } catch (error) {
        console.error('加载零件列表失败:', error);
    } finally {
        state.isLoading = false;
    }
}

// ===== 渲染：详情 Modal =====

/** 渲染单条工序行 */
function renderProcessRow(p) {
    return `
        <tr>
            <td>${p.process_order ?? '-'}</td>
            <td>${esc(p.process_seq)}</td>
            <td>${esc(p.process_code)}</td>
            <td>${p.die_sets ?? '-'}</td>
            <td>${p.tonnage ? `${p.tonnage}T` : '-'}</td>
            <td>${fmtNumber(p.cost_ratio, 4)}</td>
        </tr>
    `;
}

function renderPartDetail(part) {
    const rows = [
        ['零件号', esc(part.part_number)],
        ['零件名称', esc(part.part_name)],
        ['车型', esc(part.vehicle_model)],
        ['版本', esc(part.version)],
        ['材料', esc(part.material)],
        ['厚度', part.thickness != null ? `${part.thickness} mm` : '-'],
    ];
    const rowsRight = [
        ['重量', part.part_weight != null ? `${part.part_weight} kg` : '-'],
        ['板材尺寸', (part.sheet_length && part.sheet_width) ? `${part.sheet_length}x${part.sheet_width}` : '-'],
        ['每张板材件数', esc(part.parts_per_sheet)],
        ['板材类型', esc(part.sheet_type)],
        ['吨位', part.tonnage ? `${part.tonnage}T` : '-'],
        ['模具类型', esc(part.die_type)],
    ];
    const tableRow = ([label, value]) => `<tr><th>${label}</th><td>${value}</td></tr>`;

    const processes = part.processes || [];
    const processRows = processes.length
        ? processes.map(renderProcessRow).join('')
        : '<tr><td colspan="6" class="text-center text-muted">暂无工序数据</td></tr>';

    return `
        <div class="row">
            <div class="col-md-6">
                <table class="table table-sm">${rows.map(tableRow).join('')}</table>
            </div>
            <div class="col-md-6">
                <table class="table table-sm">${rowsRight.map(tableRow).join('')}</table>
            </div>
        </div>
        <h6 class="mt-3"><i class="bi bi-list-ol me-1"></i>工序列表</h6>
        <table class="table table-sm">
            <thead>
                <tr>
                    <th>序号</th><th>工序号</th><th>代号</th>
                    <th>模具数</th><th>吨位</th><th>成本系数</th>
                </tr>
            </thead>
            <tbody>${processRows}</tbody>
        </table>
    `;
}

async function showPartDetail(partId) {
    const modal = new bootstrap.Modal(dom.partDetailModalEl);
    modal.show();
    dom.partDetailContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
        </div>
    `;
    try {
        const response = await HttpClient.get(PARTS_API.DETAIL(partId));
        dom.partDetailContent.innerHTML = renderPartDetail(response.data);
    } catch (error) {
        dom.partDetailContent.innerHTML = `
            <div class="alert alert-danger">${esc(error.message) || '加载失败'}</div>
        `;
    }
}

async function deletePart(partId) {
    if (!confirm('确定要删除这个零件吗？')) return;
    try {
        await HttpClient.delete(PARTS_API.DELETE(partId));
        showToast('删除成功', 'success');
        loadParts(state.currentPage);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

// ===== 事件绑定（事件代理） =====

/** 操作按钮点击（详情 / 删除） */
dom.partsTableBody.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const id = Number(btn.getAttribute('data-id'));
    if (btn.getAttribute('data-action') === 'detail') showPartDetail(id);
    else if (btn.getAttribute('data-action') === 'delete') deletePart(id);
});

/** 分页点击 */
dom.pagination.addEventListener('click', (e) => {
    const link = e.target.closest('a.page-link');
    if (!link) return;
    e.preventDefault();
    const li = link.parentElement;
    if (li.classList.contains('disabled') || li.classList.contains('active')) return;
    const targetPage = parseInt(link.getAttribute('data-page'), 10);
    if (!Number.isNaN(targetPage) && targetPage >= 1) loadParts(targetPage);
});

/** 搜索输入防抖 */
dom.searchInput.addEventListener('input', () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => loadParts(1), SEARCH_DEBOUNCE_MS);
});

/** 筛选变化 */
dom.vehicleModelFilter.addEventListener('change', () => loadParts(1));
dom.versionFilter.addEventListener('change', () => loadParts(1));

// ===== 入口 =====
loadParts(1);
