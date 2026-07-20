/**
 * 汽车冲压件自动核价平台 - SPA 主应用
 *
 * 架构说明：
 * - 采用关注点分离（SoC）原则
 * - templates/    : HTML 模板片段（纯 HTML 字符串）
 * - modules/     : 页面模板模块（导出 HTML 模板函数）
 * - components/  : 可复用 UI 组件
 * - pages/       : 页面逻辑模块（初始化、数据处理）
 * - router.js    : 路由管理
 * - main.js      : 公共工具（HttpClient、Toast 等）
 */

import { templates, pageMeta } from './modules/index.js';

// ===== 页面模块 =====
// 每个页面模块必须实现 render() 和 init() 方法

const pages = {
    dashboard: {
        render() {
            return templates.dashboard;
        },
        init() {
            initDashboard();
        }
    },

    'stamping-upload': {
        render() {
            return templates.upload;
        },
        init() {
            initUploadPage();
        }
    },

    'stamping-parts': {
        render() {
            return templates.parts;
        },
        init() {
            initPartsPage();
        }
    },

    costing: {
        render() {
            return templates.costing;
        },
        init() {
            // 预留
        }
    },

    quotation: {
        render() {
            return templates.quotation;
        },
        init() {
            // 预留
        }
    },

    settings: {
        render() {
            return templates.settings;
        },
        init() {
            // 预留
        }
    },
};

// ===== 路由控制 =====

function renderPage(pageName) {
    const page = pages[pageName];
    if (!page) {
        document.getElementById('pageContent').innerHTML =
            '<div class="text-center text-slate-500 py-12">页面不存在</div>';
        return;
    }

    const content = document.getElementById('pageContent');
    const title = document.getElementById('pageTitle');
    const breadcrumb = document.getElementById('breadcrumbItem');
    const topActions = document.getElementById('topActions');

    // 更新导航高亮
    document.querySelectorAll('.sidebar-nav-link, .submenu-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === pageName) {
            link.classList.add('active');
            const parent = link.closest('.submenu');
            if (parent) parent.classList.add('show');
        }
    });

    // 更新标题
    const meta = pageMeta[pageName] || { title: pageName, breadcrumb: pageName };
    if (title) title.textContent = meta.title;
    if (breadcrumb) breadcrumb.textContent = meta.breadcrumb;
    if (topActions) topActions.innerHTML = '';

    try {
        content.innerHTML = page.render();
        page.init();
    } catch (error) {
        console.error('渲染页面失败:', error);
        content.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-600">加载失败: ${esc(error.message)}</div>`;
    }
}

// ===== 仪表盘初始化 =====

async function initDashboard() {
    showLoading();
    try {
        const [partsRes, processesRes, modelsRes] = await Promise.allSettled([
            HttpClient.get('/api/dashboard/stats/parts'),
            HttpClient.get('/api/dashboard/stats/processes'),
            HttpClient.get('/api/dashboard/stats/models'),
        ]);

        const totalParts = partsRes.status === 'fulfilled' ? (partsRes.value.data?.count || 0) : '-';
        const totalProcesses = processesRes.status === 'fulfilled' ? (processesRes.value.data?.count || 0) : '-';
        const totalModels = modelsRes.status === 'fulfilled' ? (modelsRes.value.data?.count || 0) : '-';

        const el = document.getElementById('totalParts');
        if (el) el.textContent = totalParts;

        const elProcesses = document.getElementById('totalProcesses');
        if (elProcesses) elProcesses.textContent = totalProcesses;

        const elModels = document.getElementById('totalModels');
        if (elModels) elModels.textContent = totalModels;
    } catch (error) {
        console.error('加载统计数据失败:', error);
    } finally {
        hideLoading();
    }
}

// ===== 上传页面初始化 =====

function initUploadPage() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('filePreview');
    const uploadForm = document.getElementById('uploadForm');

    if (!uploadZone || !fileInput) return;

    // 点击上传区域
    uploadZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
            fileInput.click();
        }
    });

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        handleUploadFiles(e.target.files);
    });

    // 拖拽上传
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('bg-white', 'border-slate-400');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('bg-white', 'border-slate-400');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('bg-white', 'border-slate-400');
        handleUploadFiles(e.dataTransfer.files);
    });

    // 表单提交
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleUploadSubmit();
    });

    function handleUploadFiles(files) {
        if (!files || files.length === 0) return;

        const file = files[0];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const allowedExts = ['.xlsx', '.xls'];

        if (!allowedExts.includes(ext)) {
            showToast('不支持的文件格式，请上传 .xlsx 或 .xls 文件', 'warning');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            showToast('文件过大，最大支持 50MB', 'warning');
            return;
        }

        preview.classList.remove('hidden');
        preview.innerHTML = `
            <div class="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-md">
                <span class="text-green-600">${svgIcon('file-earmark-excel')}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-slate-900 truncate">${esc(file.name)}</div>
                    <div class="text-xs text-slate-500">${formatFileSize(file.size)}</div>
                </div>
                <button type="button" onclick="window.removeUploadFile()" class="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                    ${svgIcon('trash')}
                </button>
            </div>
        `;

        uploadZone.classList.add('border-green-400', 'bg-green-50/50');
        document.getElementById('uploadTitle').textContent = '已选择文件';
        document.getElementById('uploadHint').textContent = file.name;
    }

    function handleUploadSubmit() {
        const vehicleModel = document.getElementById('vehicleModel');
        const version = document.getElementById('version');
        const fileInput = document.getElementById('fileInput');

        if (!vehicleModel.value.trim()) {
            showToast('请输入车型', 'warning');
            vehicleModel.focus();
            return;
        }

        if (!version.value.trim()) {
            showToast('请输入版本', 'warning');
            version.focus();
            return;
        }

        if (!fileInput.files || fileInput.files.length === 0) {
            showToast('请选择文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('vehicle_model', vehicleModel.value.trim());
        formData.append('version', version.value.trim());
        formData.append('file', fileInput.files[0]);

        document.getElementById('submitBtn').disabled = true;

        HttpClient.post('/api/stamping/upload/', formData)
            .then(() => {
                showToast('文件上传成功', 'success');
                window.resetUploadForm();
            })
            .catch(error => {
                console.error('上传失败:', error);
                showToast(error.message || '上传失败', 'danger');
            })
            .finally(() => {
                document.getElementById('submitBtn').disabled = false;
            });
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ===== 零件列表页面 =====

const partsState = {
    currentPage: 1,
    pageSize: 10,
    isLoading: false,
    searchTimer: null,
};

const PARTS_CONFIG = {
    DEFAULT_PAGE_SIZE: 10,
    PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
    SEARCH_DEBOUNCE_MS: 400,
    STORAGE_KEY: 'parts_page_size',
};

function initPartsPage() {
    const dom = {
        searchInput: document.getElementById('searchInput'),
        vehicleModelFilter: document.getElementById('vehicleModelFilter'),
        versionFilter: document.getElementById('versionFilter'),
        pageSizeSelect: document.getElementById('pageSizeSelect'),
        totalCount: document.getElementById('totalCount'),
        partsTableBody: document.getElementById('partsTableBody'),
        pagination: document.getElementById('pagination'),
    };

    // 初始化每页数量
    const savedSize = localStorage.getItem(PARTS_CONFIG.STORAGE_KEY);
    partsState.pageSize = PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(parseInt(savedSize))
        ? parseInt(savedSize)
        : PARTS_CONFIG.DEFAULT_PAGE_SIZE;
    if (dom.pageSizeSelect) dom.pageSizeSelect.value = partsState.pageSize;

    // 搜索输入防抖
    dom.searchInput?.addEventListener('input', () => {
        clearTimeout(partsState.searchTimer);
        partsState.searchTimer = setTimeout(() => loadParts(1), PARTS_CONFIG.SEARCH_DEBOUNCE_MS);
    });

    // 筛选变化
    dom.vehicleModelFilter?.addEventListener('change', () => loadParts(1));
    dom.versionFilter?.addEventListener('change', () => loadParts(1));

    // 每页数量变化
    dom.pageSizeSelect?.addEventListener('change', (e) => {
        const newSize = parseInt(e.target.value, 10);
        if (newSize && PARTS_CONFIG.PAGE_SIZE_OPTIONS.includes(newSize)) {
            partsState.pageSize = newSize;
            localStorage.setItem(PARTS_CONFIG.STORAGE_KEY, String(newSize));
            loadParts(1);
        }
    });

    // 表格操作按钮
    dom.partsTableBody?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const id = Number(btn.getAttribute('data-id'));
        const action = btn.getAttribute('data-action');
        if (action === 'detail') showPartDetail(id);
        else if (action === 'delete') deletePart(id);
    });

    // 分页点击
    dom.pagination?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-page]');
        if (!btn || btn.disabled) return;
        const targetPage = parseInt(btn.getAttribute('data-page'), 10);
        if (!Number.isNaN(targetPage) && targetPage >= 1) loadParts(targetPage);
    });

    // 加载数据
    loadParts(1);
}

async function loadParts(page = 1) {
    if (partsState.isLoading) return;
    partsState.isLoading = true;
    partsState.currentPage = page;

    const dom = {
        searchInput: document.getElementById('searchInput'),
        vehicleModelFilter: document.getElementById('vehicleModelFilter'),
        versionFilter: document.getElementById('versionFilter'),
        totalCount: document.getElementById('totalCount'),
        partsTableBody: document.getElementById('partsTableBody'),
        pagination: document.getElementById('pagination'),
    };

    const params = {
        page: page,
        size: partsState.pageSize,
    };

    const partNumber = dom.searchInput?.value.trim();
    const vehicleModel = dom.vehicleModelFilter?.value;
    const version = dom.versionFilter?.value;
    if (partNumber) params.part_number = partNumber;
    if (vehicleModel) params.vehicle_model = vehicleModel;
    if (version) params.version = version;

    try {
        const result = await HttpClient.get('/api/stamping/parts/list', { params });
        const pageInfo = result.data || {};
        renderParts(pageInfo.list || [], dom);
        renderPartsPagination(pageInfo, dom);
        if (dom.totalCount) dom.totalCount.textContent = `共 ${pageInfo.total || 0} 个零件`;
    } catch (error) {
        console.error('加载零件列表失败:', error);
        if (dom.partsTableBody) {
            dom.partsTableBody.innerHTML = `
                <tr><td colspan="9">
                    <div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-600 text-center">
                        加载失败: ${esc(error.message)}
                    </div>
                </td></tr>
            `;
        }
    } finally {
        partsState.isLoading = false;
    }
}

function renderParts(parts, dom) {
    if (!parts || parts.length === 0) {
        dom.partsTableBody.innerHTML = `
            <tr><td colspan="9">
                <div class="flex flex-col items-center justify-center py-16 text-slate-400">
                    <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                        <span class="text-slate-300">${svgIcon('inbox')}</span>
                    </div>
                    <h5 class="text-slate-600 font-medium mb-1">暂无零件数据</h5>
                    <p class="text-sm text-slate-400">请联系管理员导入工艺文件</p>
                </div>
            </td></tr>
        `;
        return;
    }

    dom.partsTableBody.innerHTML = parts.map((part, index) => renderPartRow(part, index)).join('');
}

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
                        ${svgIcon('eye')}
                    </button>
                    <button class="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-150" data-action="delete" data-id="${part.id}" title="删除">
                        ${svgIcon('trash')}
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function renderPartsPagination(pageInfo) {
    const { total, page, total_pages, has_next, has_prev } = pageInfo;
    const pagination = document.getElementById('pagination');
    if (!pagination) return;

    if (!total_pages || total_pages <= 1) {
        pagination.innerHTML = '';
        return;
    }

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
                ${svgIcon('chevron-left')}
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
            ${svgIcon('chevron-right')}
        </button>
        </nav>
    `;

    pagination.innerHTML = html;
}

async function showPartDetail(partId) {
    const modalEl = document.getElementById('partDetailModal');
    const contentEl = document.getElementById('partDetailContent');

    if (typeof bootstrap !== 'undefined' && modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }

    contentEl.innerHTML = `
        <div class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-2 border-slate-200 border-t-slate-600 rounded-full animate-spin"></div>
        </div>
    `;

    try {
        const response = await HttpClient.get(`/api/stamping/parts/${partId}`);
        contentEl.innerHTML = renderPartDetail(response.data);
    } catch (error) {
        contentEl.innerHTML = `
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex items-center gap-2 text-red-600">
                    ${svgIcon('exclamation-circle')}
                    <span class="text-sm font-medium">${esc(error.message) || '加载失败'}</span>
                </div>
            </div>
        `;
    }
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
        ? processes.map(p => `
            <tr class="border-b border-slate-100 last:border-b-0">
                <td class="px-3 py-2 text-sm text-slate-600">${p.process_order ?? '-'}</td>
                <td class="px-3 py-2 text-sm text-slate-700">${esc(p.process_seq)}</td>
                <td class="px-3 py-2 text-sm text-slate-700">${esc(p.process_code)}</td>
                <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${p.die_sets ?? '-'}</td>
                <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${p.tonnage ? `${p.tonnage}T` : '-'}</td>
                <td class="px-3 py-2 text-sm text-right font-mono tabular-nums text-slate-700">${fmtNum(p.cost_ratio, 4)}</td>
            </tr>
        `).join('')
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
                <span class="text-slate-400">${svgIcon('list-ol')}</span>
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

async function deletePart(partId) {
    if (!confirm('确定要删除这个零件吗？')) return;
    try {
        await HttpClient.delete(`/api/stamping/parts/${partId}`);
        showToast('删除成功', 'success');
        loadParts(partsState.currentPage);
    } catch (error) {
        console.error('删除失败:', error);
        showToast(error.message || '删除失败', 'danger');
    }
}

// ===== 全局函数 =====

window.removeUploadFile = function() {
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('filePreview');
    const uploadZone = document.getElementById('uploadZone');

    if (fileInput) fileInput.value = '';
    if (preview) preview.classList.add('hidden');
    if (uploadZone) {
        uploadZone.classList.remove('border-green-400', 'bg-green-50/50');
        document.getElementById('uploadTitle').textContent = '拖拽文件到此处上传';
        document.getElementById('uploadHint').textContent = '或点击选择文件';
    }
};

window.resetUploadForm = function() {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.reset();
        window.removeUploadFile();
    }
};

// ===== 初始化 =====

document.addEventListener('DOMContentLoaded', function() {
    // 页面导航
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const pageName = this.getAttribute('data-page');
            renderPage(pageName);
        });
    });

    // 初始化侧边栏子菜单
    document.querySelectorAll('[data-submenu-toggle]').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const submenuId = this.getAttribute('data-submenu-toggle');
            const submenu = document.getElementById(submenuId);
            const parent = this.closest('.has-submenu');

            if (!submenu || !parent) return;

            const isOpen = submenu.classList.contains('show');

            // 关闭所有其他子菜单
            document.querySelectorAll('.has-submenu.open').forEach(item => {
                if (item !== parent) {
                    item.classList.remove('open');
                    const otherSubmenu = item.querySelector('.submenu');
                    if (otherSubmenu) otherSubmenu.classList.remove('show');
                }
            });

            // 切换当前菜单
            if (isOpen) {
                parent.classList.remove('open');
                submenu.classList.remove('show');
            } else {
                parent.classList.add('open');
                submenu.classList.add('show');
            }
        });
    });

    // 初始化仪表盘
    renderPage('dashboard');
});
