/**
 * 冲压零件列表页脚本
 * 遵循 docs/front-end.mdc 规范：仅使用 Tailwind 类名
 *
 * 依赖（由模板注入）：
 *   - PARTS_API              { LIST, DETAIL(id), DELETE(id) }
 *   - PARTS_CONFIG           { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, SEARCH_DEBOUNCE_MS, STORAGE_KEY }
 */

// ===== 工具函数 =====

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
    pageSizeSelect:     document.getElementById('pageSizeSelect'),
    totalCount:         document.getElementById('totalCount'),
    partsTableBody:     document.getElementById('partsTableBody'),
    pagination:         document.getElementById('pagination'),
    partDetailContent:  document.getElementById('partDetailContent'),
    partDetailModalEl:  document.getElementById('partDetailModal'),
};

// ===== 状态 =====

const state = {
    currentPage: 1,
    pageSize: PARTS_CONFIG.DEFAULT_PAGE_SIZE,
    isLoading: false,
    searchTimer: null,
};

// ===== 本地存储偏好 =====

/** 从 LocalStorage 加载每页数量偏好 */
function loadPageSizePreference() {
    try {
        const saved = localStorage.getItem(PARTS_CONFIG.STORAGE_KEY);
        if (saved) {
            const parsed = parseInt(saved, 10);
            if (PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(parsed)) {
                return parsed;
            }
        }
    } catch (e) {
        console.warn('Failed to load page size preference:', e);
    }
    return PARTS_CONFIG.DEFAULT_PAGE_SIZE;
}

/** 保存每页数量偏好到 LocalStorage */
function savePageSizePreference(pageSize) {
    try {
        localStorage.setItem(PARTS_CONFIG.STORAGE_KEY, String(pageSize));
    } catch (e) {
        console.warn('Failed to save page size preference:', e);
    }
}

/** 初始化每页数量选择器 */
function initPageSizeSelector() {
    const preferredSize = loadPageSizePreference();
    state.pageSize = preferredSize;

    if (dom.pageSizeSelect) {
        dom.pageSizeSelect.value = String(preferredSize);
    }
}

// ===== 渲染：表格行 =====

/** 空状态 HTML（Tailwind CSS，与 _macros.html empty_state 宏一致） */
function renderEmptyRow(message = '暂无零件数据', hint = '请联系管理员导入工艺文件', colspan = 9) {
    return `
        <tr><td colspan="${colspan}">
            <div class="flex flex-col items-center justify-center py-16 text-slate-400">
                <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                    <i class="bi bi-inbox text-3xl text-slate-300"></i>
                </div>
                <h5 class="text-slate-600 font-medium mb-1">${esc(message)}</h5>
                <p class="text-sm text-slate-400">${esc(hint)}</p>
            </div>
        </td></tr>
    `;
}

/** 数字格式化：null/undefined/NaN → '-'，保留指定小数位 */
const fmtNum = (value, digits = 2) => {
    if (value == null || Number.isNaN(value)) return '-';
    return Number(value).toFixed(digits);
};

/** 渲染单条零件行（Tailwind CSS，与 Jinja2 模板一致）
 * 交互：操作按钮通过 group 机制，行悬停时显示
 * 设计：奇偶行交替 bg，h-16 行高，悬停加深背景
 */
function renderPartRow(part, index) {
    const thickness = fmtNum(part.thickness, 2);
    const partWeight = fmtNum(part.part_weight, 3);
    const processCount = part.process_count != null ? part.process_count : '-';
    const evenBg = index % 2 === 1 ? 'bg-slate-50/50' : '';
    return `
        <tr class="group h-16 border-b border-slate-100 ${evenBg} hover:bg-slate-100/80 transition-colors duration-150">
            <td class="px-5 py-4"><strong class="text-slate-800">${esc(part.part_number)}</strong></td>
            <td class="px-5 py-4 text-slate-600">${esc(part.part_name) || '-'}</td>
            <td class="px-5 py-4 text-center">
                <span class="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md text-xs font-medium">${esc(part.vehicle_model) || '-'}</span>
            </td>
            <td class="px-5 py-4 text-center text-slate-600">${esc(part.version) || '-'}</td>
            <td class="px-5 py-4 text-slate-600">${esc(part.material) || '-'}</td>
            <td class="px-5 py-4 text-right font-mono tabular-nums text-slate-800">${thickness}</td>
            <td class="px-5 py-4 text-right font-mono tabular-nums text-slate-800">${partWeight}</td>
            <td class="px-5 py-4 text-right font-mono tabular-nums text-slate-800">${processCount}</td>
            <td class="px-5 py-4 text-center">
                <div class="flex items-center justify-center gap-1">
                    <button class="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition-all duration-150" data-action="detail" data-id="${part.id}" title="查看详情">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-150" data-action="delete" data-id="${part.id}" title="删除">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function renderParts(parts) {
    if (!parts || parts.length === 0) {
        dom.partsTableBody.innerHTML = renderEmptyRow();
        return;
    }
    dom.partsTableBody.innerHTML = parts.map((part, index) => renderPartRow(part, index)).join('');
}

// ===== 渲染：分页 =====

function renderPagination(pageInfo) {
    const { total, page, total_pages, has_next, has_prev } = pageInfo;
    const totalCountEl = document.getElementById('totalCount');

    if (totalCountEl) {
        totalCountEl.textContent = `共 ${total} 个零件`;
    }

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
        <nav class="flex items-center justify-center gap-1">
            <button class="p-2 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                    data-page="${page - 1}" ${!has_prev ? 'disabled' : ''}>
                <i class="bi bi-chevron-left"></i>
            </button>
    `;

    let lastPage = 0;
    for (const p of sortedPages) {
        if (lastPage && p - lastPage > 1) {
            html += `<span class="px-2 text-slate-400">...</span>`;
        }
        const isActive = p === page;
        html += `
            <button class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors
                ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}"
                data-page="${p}">
                ${p}
            </button>
        `;
        lastPage = p;
    }

    html += `
        <button class="p-2 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                data-page="${page + 1}" ${!has_next ? 'disabled' : ''}>
            <i class="bi bi-chevron-right"></i>
        </button>
        </nav>
    `;

    dom.pagination.innerHTML = html;
}

// ===== 数据加载 =====

async function loadParts(page = 1) {
    if (state.isLoading) return;
    state.isLoading = true;
    state.currentPage = page;

    const params = {
        page: page,
        size: state.pageSize,
    };

    const partNumber = dom.searchInput?.value.trim();
    const vehicleModel = dom.vehicleModelFilter?.value;
    const version = dom.versionFilter?.value;
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
        <tr class="border-b border-slate-100 last:border-b-0">
            <td class="px-3 py-2 text-sm text-slate-600">${p.process_order ?? '-'}</td>
            <td class="px-3 py-2 text-sm text-slate-700">${esc(p.process_seq)}</td>
            <td class="px-3 py-2 text-sm text-slate-700">${esc(p.process_code)}</td>
            <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${p.die_sets ?? '-'}</td>
            <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${p.tonnage ? `${p.tonnage}T` : '-'}</td>
            <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${fmtNum(p.cost_ratio, 4)}</td>
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
    const tableRow = ([label, value]) => `
        <tr class="border-b border-slate-100 last:border-b-0">
            <th class="px-3 py-2 text-left text-xs font-medium text-slate-500 w-28">${label}</th>
            <td class="px-3 py-2 text-sm text-slate-700">${value}</td>
        </tr>
    `;

    const processes = part.processes || [];
    const processRows = processes.length
        ? processes.map(renderProcessRow).join('')
        : `<tr><td colspan="6" class="px-3 py-6 text-center text-sm text-slate-400">暂无工序数据</td></tr>`;

    return `
        <div class="grid grid-cols-2 gap-4 mb-4">
            <div class="bg-slate-50 rounded-md overflow-hidden">
                <table class="w-full text-xs">${rows.map(tableRow).join('')}</table>
            </div>
            <div class="bg-slate-50 rounded-md overflow-hidden">
                <table class="w-full text-xs">${rowsRight.map(tableRow).join('')}</table>
            </div>
        </div>
        <div class="border border-slate-200 rounded-md overflow-hidden">
            <div class="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
                <i class="bi bi-list-ol text-slate-400"></i>
                <span class="text-sm font-medium text-slate-700">工序列表</span>
            </div>
            <table class="w-full">
                <thead>
                    <tr class="bg-slate-50 border-b border-slate-200">
                        <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">序号</th>
                        <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">工序号</th>
                        <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">代号</th>
                        <th class="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">模具数</th>
                        <th class="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">吨位</th>
                        <th class="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">成本系数</th>
                    </tr>
                </thead>
                <tbody>${processRows}</tbody>
            </table>
        </div>
    `;
}

/** 显示详情 Modal */
function showPartDetail(partId) {
    // 使用 Bootstrap Modal（已在 base.html 引入）
    if (typeof bootstrap !== 'undefined' && dom.partDetailModalEl) {
        const modal = new bootstrap.Modal(dom.partDetailModalEl);
        modal.show();
    }

    dom.partDetailContent.innerHTML = `
        <div class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-2 border-slate-200 border-t-slate-600 rounded-full animate-spin"></div>
        </div>
    `;

    HttpClient.get(PARTS_API.DETAIL(partId))
        .then(response => {
            dom.partDetailContent.innerHTML = renderPartDetail(response.data);
        })
        .catch(error => {
            dom.partDetailContent.innerHTML = `
                <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                    <div class="flex items-center gap-2 text-red-600">
                        <i class="bi bi-exclamation-circle"></i>
                        <span class="text-sm font-medium">${esc(error.message) || '加载失败'}</span>
                    </div>
                </div>
            `;
        });
}

/** 删除零件 */
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
dom.partsTableBody?.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const id = Number(btn.getAttribute('data-id'));
    if (btn.getAttribute('data-action') === 'detail') showPartDetail(id);
    else if (btn.getAttribute('data-action') === 'delete') deletePart(id);
});

/** 分页点击 */
dom.pagination?.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-page]');
    if (!btn || btn.disabled) return;
    const targetPage = parseInt(btn.getAttribute('data-page'), 10);
    if (!Number.isNaN(targetPage) && targetPage >= 1) loadParts(targetPage);
});

/** 搜索输入防抖 */
dom.searchInput?.addEventListener('input', () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => loadParts(1), PARTS_CONFIG.SEARCH_DEBOUNCE_MS);
});

/** 筛选变化 */
dom.vehicleModelFilter?.addEventListener('change', () => loadParts(1));
dom.versionFilter?.addEventListener('change', () => loadParts(1));

/** 每页数量变化：保存偏好并刷新 */
dom.pageSizeSelect?.addEventListener('change', (e) => {
    const newSize = parseInt(e.target.value, 10);
    if (newSize && PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(newSize)) {
        state.pageSize = newSize;
        savePageSizePreference(newSize);
        loadParts(1); // 重置到第一页
    }
});

// ===== 入口 =====

initPageSizeSelector();
loadParts(1);
