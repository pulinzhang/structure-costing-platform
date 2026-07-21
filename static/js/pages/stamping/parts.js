/**
 * Stamping Parts Page Module
 * 冲压零件列表页面逻辑
 */
import { partsTemplate, detailModalTemplate } from '../templates/stamping/parts.html.js';

export const StampingPartsPage = {
    state: {
        currentPage: 1,
        pageSize: 10,
        isLoading: false,
        searchTimer: null,
    },

    config: {
        DEFAULT_PAGE_SIZE: 10,
        PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
        SEARCH_DEBOUNCE_MS: 400,
        STORAGE_KEY: 'parts_page_size',
    },

    /**
     * 初始化页面
     */
    init() {
        this.initState();
        this.bindEvents();
        this.loadParts(1);
    },

    /**
     * 初始化状态
     */
    initState() {
        const savedSize = localStorage.getItem(this.config.STORAGE_KEY);
        this.state.pageSize = this.config.PAGE_SIZE_OPTIONS.includes(parseInt(savedSize))
            ? parseInt(savedSize)
            : this.config.DEFAULT_PAGE_SIZE;

        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) pageSizeSelect.value = this.state.pageSize;
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        const searchInput = document.getElementById('searchInput');
        const vehicleModelFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');
        const pageSizeSelect = document.getElementById('pageSizeSelect');
        const partsTableBody = document.getElementById('partsTableBody');
        const pagination = document.getElementById('pagination');

        // 搜索防抖
        searchInput?.addEventListener('input', () => {
            clearTimeout(this.state.searchTimer);
            this.state.searchTimer = setTimeout(() => this.loadParts(1), this.config.SEARCH_DEBOUNCE_MS);
        });

        // 筛选变化
        vehicleModelFilter?.addEventListener('change', () => this.loadParts(1));
        versionFilter?.addEventListener('change', () => this.loadParts(1));

        // 每页数量变化
        pageSizeSelect?.addEventListener('change', (e) => {
            const newSize = parseInt(e.target.value, 10);
            if (newSize && this.config.PAGE_SIZE_OPTIONS.includes(newSize)) {
                this.state.pageSize = newSize;
                localStorage.setItem(this.config.STORAGE_KEY, String(newSize));
                this.loadParts(1);
            }
        });

        // 表格操作按钮
        partsTableBody?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            const id = Number(btn.getAttribute('data-id'));
            const action = btn.getAttribute('data-action');
            if (action === 'detail') this.showPartDetail(id);
            else if (action === 'delete') this.deletePart(id);
        });

        // 分页点击
        pagination?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-page]');
            if (!btn || btn.disabled) return;
            const targetPage = parseInt(btn.getAttribute('data-page'), 10);
            if (!Number.isNaN(targetPage) && targetPage >= 1) this.loadParts(targetPage);
        });
    },

    /**
     * 加载零件列表
     */
    async loadParts(page = 1) {
        if (this.state.isLoading) return;
        this.state.isLoading = true;
        this.state.currentPage = page;

        const searchInput = document.getElementById('searchInput');
        const vehicleModelFilter = document.getElementById('vehicleModelFilter');
        const versionFilter = document.getElementById('versionFilter');
        const totalCount = document.getElementById('totalCount');
        const partsTableBody = document.getElementById('partsTableBody');
        const pagination = document.getElementById('pagination');

        const params = {
            page: page,
            size: this.state.pageSize,
        };

        const partNumber = searchInput?.value.trim();
        const vehicleModel = vehicleModelFilter?.value;
        const version = versionFilter?.value;
        if (partNumber) params.part_number = partNumber;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        if (version) params.version = version;

        try {
            const result = await HttpClient.get('/api/stamping/parts/list', { params });
            const pageInfo = result.data || {};

            this.renderParts(pageInfo.list || []);
            this.renderPagination(pageInfo);
            if (totalCount) totalCount.textContent = `共 ${pageInfo.total || 0} 个零件`;
        } catch (error) {
            console.error('加载零件列表失败:', error);
            if (partsTableBody) {
                partsTableBody.innerHTML = `
                    <tr><td colspan="9">
                        <div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-600 text-center">
                            加载失败: ${esc(error.message)}
                        </div>
                    </td></tr>
                `;
            }
        } finally {
            this.state.isLoading = false;
        }
    },

    /**
     * 渲染零件列表
     */
    renderParts(parts) {
        const partsTableBody = document.getElementById('partsTableBody');
        if (!partsTableBody) return;

        const inboxIcon = `<svg class="inline-block w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`;
        const eyeIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
        const trashIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`;
        const chevronLeftIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg>`;
        const chevronRightIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>`;
        const exclamationIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`;
        const listIcon = `<svg class="inline-block w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 6h11"/><path d="M10 12h11"/><path d="M10 18h11"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>`;

        if (!parts || parts.length === 0) {
            partsTableBody.innerHTML = `
                <tr><td colspan="9">
                    <div class="flex flex-col items-center justify-center py-16 text-slate-400">
                        <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                            <span class="text-slate-300">${inboxIcon}</span>
                        </div>
                        <h5 class="text-slate-600 font-medium mb-1">暂无零件数据</h5>
                        <p class="text-sm text-slate-400">请联系管理员导入工艺文件</p>
                    </div>
                </td></tr>
            `;
            return;
        }

        partsTableBody.innerHTML = parts.map((part, index) => this.renderPartRow(part, index, eyeIcon, trashIcon)).join('');
    },

    /**
     * 渲染单行零件
     */
    renderPartRow(part, index, eyeIcon, trashIcon) {
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
                            ${eyeIcon}
                        </button>
                        <button class="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-150" data-action="delete" data-id="${part.id}" title="删除">
                            ${trashIcon}
                        </button>
                    </div>
                </td>
            </tr>
        `;
    },

    /**
     * 渲染分页
     */
    renderPagination(pageInfo) {
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
                    ${chevronLeftIcon}
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
                ${chevronRightIcon}
            </button>
            </nav>
        `;

        pagination.innerHTML = html;
    },

    /**
     * 显示零件详情
     */
    async showPartDetail(partId) {
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
            contentEl.innerHTML = this.renderPartDetail(response.data);
        } catch (error) {
            contentEl.innerHTML = `
                <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                    <div class="flex items-center gap-2 text-red-600">
                        <i class="bi bi-exclamation-circle"></i>
                        <span class="text-sm font-medium">${esc(error.message) || '加载失败'}</span>
                    </div>
                </div>
            `;
        }
    },

    /**
     * 渲染零件详情
     */
    renderPartDetail(part) {
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
    },

    /**
     * 删除零件
     */
    async deletePart(partId) {
        if (!confirm('确定要删除这个零件吗？')) return;
        try {
            await HttpClient.delete(`/api/stamping/parts/${partId}`);
            showToast('删除成功', 'success');
            this.loadParts(this.state.currentPage);
        } catch (error) {
            console.error('删除失败:', error);
            showToast(error.message || '删除失败', 'danger');
        }
    },

    /**
     * 渲染页面内容
     */
    render() {
        return partsTemplate() + detailModalTemplate();
    }
};
