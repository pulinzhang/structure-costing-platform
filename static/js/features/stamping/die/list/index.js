import { dieListTemplate } from './template.js?v=10';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
    normalizePageSize,
} from '../../../../page-size.js?v=3';
import { setSearchBusy } from '../../../../search-busy.js?v=1';
import { partShortCodeCellHtml, partNumberNameCellHtml, shortPartNumber } from '../../../../part-identity.js?v=3';
import {
    asOfFilterHtml,
    fillAsOfSelects,
    fillYearMonthSelects,
    fmtPeriodRange,
    periodEditorHtml,
    readAsOf,
    readPeriod,
    wallClockYearMonth,
} from '../../../common/period-ui.js?v=2';

const STORAGE_KEY = 'dieListPageSize';

const dieState = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    items: [],
    isLoading: false,
};

function dieDimMm(value) {
    if (value == null || value === '') return '—';
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return String(Math.round(number));
}

export const DieListPage = {
    canUpdate: true,
    canDelete: true,
    canExport: true,

    init() {
        this.canUpdate = typeof can === 'function' ? can('op:stamping-die-list:update') : true;
        this.canDelete = typeof can === 'function' ? can('op:stamping-die-list:delete') : true;
        this.canExport = typeof can === 'function' ? can('op:stamping-die-list:export') : true;
        dieState.pageSize = normalizePageSize(localStorage.getItem(STORAGE_KEY));
        if (!this.canDelete) document.getElementById('dieBatchDeleteBtn')?.classList.add('hidden');
        if (!this.canExport) document.getElementById('dieExportBtn')?.classList.add('hidden');
        const asOfHost = document.getElementById('dieListAsOfFilters');
        if (asOfHost && !document.getElementById('dieListYear')) {
            asOfHost.innerHTML = asOfFilterHtml('dieList', { variant: 'die' });
            const clock = wallClockYearMonth();
            fillAsOfSelects('dieList', clock.year, clock.month);
        }
        this.bindEvents();
        bindPagination({
            selectId: 'dieListPageSize',
            buttonsId: 'dieListPagination',
            getSize: () => dieState.pageSize,
            setSize: (size) => {
                dieState.pageSize = size;
                localStorage.setItem(STORAGE_KEY, String(size));
            },
            onPage: (page) => this.loadList(page),
        });
        this.loadFilters();
        this.renderEmpty('请先选择基地和项目', '未选齐范围时不会请求列表');
    },

    bindEvents() {
        const pageContent = document.getElementById('pageContent');
        document.getElementById('dieListLocation')?.addEventListener('change', () => {
            this.loadFilters(true).then(() => this.loadList(1));
        });
        document.getElementById('dieListVehicle')?.addEventListener('change', () => {
            this.loadList(1);
        });
        document.getElementById('dieListSearchBtn')?.addEventListener('click', () => this.loadList(1));
        document.getElementById('dieListPartNumber')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.loadList(1);
            }
        });
        document.getElementById('dieBatchDeleteBtn')?.addEventListener('click', () => this.batchDelete());
        document.getElementById('dieExportBtn')?.addEventListener('click', () => this.exportExcel());
        document.getElementById('dieDrawerCloseBtn')?.addEventListener('click', () => this.closeDrawer());
        document.getElementById('dieDrawerBackdrop')?.addEventListener('click', () => this.closeDrawer());
        pageContent?.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('button[data-action]');
            if (actionBtn) {
                e.stopPropagation();
                if (actionBtn.getAttribute('data-action') === 'detail') {
                    this.showDetail(Number(actionBtn.getAttribute('data-id')));
                }
                return;
            }
        });
    },

    fillSelect(id, values, placeholder) {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        const options = [`<option value="">${esc(placeholder)}</option>`];
        (values || []).forEach((value) => {
            const text = String(value);
            options.push(`<option value="${esc(text)}"${text === current ? ' selected' : ''}>${esc(text)}</option>`);
        });
        select.innerHTML = options.join('');
    },

    async loadFilters(resetVehicle = false) {
        const location = document.getElementById('dieListLocation')?.value || '';
        if (resetVehicle) {
            const el = document.getElementById('dieListVehicle');
            if (el) el.value = '';
        }
        try {
            const res = await HttpClient.get('/api/stamping/die/filters', {
                params: location ? { location } : {},
            });
            const data = res.data || {};
            this.fillSelect('dieListLocation', data.locations || [], '请选择');
            if (location) {
                const locEl = document.getElementById('dieListLocation');
                if (locEl) locEl.value = location;
            }
            this.fillSelect(
                'dieListVehicle',
                data.vehicle_models || [],
                location ? '请选择项目' : '请先选择基地'
            );
        } catch (error) {
            showToast(error.message || '加载筛选项失败', 'error');
        }
    },

    collectScope() {
        return {
            location: document.getElementById('dieListLocation')?.value?.trim() || '',
            vehicle_model: document.getElementById('dieListVehicle')?.value?.trim() || '',
        };
    },

    collectListFilters() {
        const asOf = readAsOf('dieList') || wallClockYearMonth();
        return {
            ...this.collectScope(),
            part_number: document.getElementById('dieListPartNumber')?.value?.trim() || '',
            year: asOf.year,
            month: asOf.month,
        };
    },

    requireScope(actionLabel) {
        const scope = this.collectScope();
        if (!scope.location || !scope.vehicle_model) {
            showToast(`${actionLabel}须先选择基地和项目`, 'warning');
            return null;
        }
        return scope;
    },

    renderEmpty(title, hint) {
        const empty = document.getElementById('dieListEmpty');
        const body = document.getElementById('dieListTableBody');
        if (body) body.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        const t = document.getElementById('dieListEmptyTitle');
        const h = document.getElementById('dieListEmptyHint');
        if (t) t.textContent = title;
        if (h) h.textContent = hint;
        document.getElementById('dieListTotalLabel').textContent = '';
        document.getElementById('dieListPagination').innerHTML = '';
        document.getElementById('dieHudTotal').textContent = '—';
        document.getElementById('dieHudScope').textContent = '请选择基地与项目';
    },

    async loadList(page) {
        const scope = this.collectScope();
        if (!scope.location || !scope.vehicle_model) {
            this.renderEmpty('请先选择基地和项目', '未选齐范围时不会请求列表');
            return;
        }
        if (dieState.isLoading) return;
        const filters = this.collectListFilters();
        dieState.page = page || 1;
        dieState.isLoading = true;
        setSearchBusy('dieListSearchBtn', true);
        const empty = document.getElementById('dieListEmpty');
        const loading = document.getElementById('dieListLoading');
        empty?.classList.add('hidden');
        loading?.classList.remove('hidden');
        try {
            const res = await HttpClient.get('/api/stamping/die/parts', {
                params: {
                    location: filters.location,
                    vehicle_model: filters.vehicle_model,
                    part_number: filters.part_number || undefined,
                    year: filters.year,
                    month: filters.month,
                    page: dieState.page,
                    size: dieState.pageSize,
                },
            });
            const data = res.data || {};
            dieState.items = data.items || [];
            dieState.total = data.total || 0;
            document.getElementById('dieHudScope').textContent =
                `${filters.location} / ${filters.vehicle_model}`;
            document.getElementById('dieHudTotal').textContent = String(dieState.total);
            this.renderRows();
            document.getElementById('dieListTotalLabel').textContent = `共 ${dieState.total} 条`;
            paintPagination(
                'dieListPagination',
                dieState.page,
                dieState.total > 0 ? Math.ceil(dieState.total / dieState.pageSize) : 0,
            );
            if (!dieState.items.length) {
                this.renderEmpty('本范围暂无模具数据', '请先上传模具布点清单');
            } else {
                empty?.classList.add('hidden');
            }
        } catch (error) {
            this.renderEmpty('加载失败', error.message || '请稍后重试');
        } finally {
            dieState.isLoading = false;
            setSearchBusy('dieListSearchBtn', false);
            loading?.classList.add('hidden');
        }
    },

    renderRows() {
        const body = document.getElementById('dieListTableBody');
        if (!body) return;
        const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
        body.innerHTML = dieState.items.map((row) => {
            return `
                <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
                    <td class="p-0 relative">
                        <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                    </td>
                    <td class="px-2 py-2 text-[#8E8E93]">${esc(row.seq_no ?? '-')}</td>
                    <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                        ${partShortCodeCellHtml(row.part_number)}
                    </td>
                    <td class="px-2 py-2 overflow-hidden">
                        ${partNumberNameCellHtml(row.part_number, row.part_name)}
                    </td>
                    <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.die_type)}</td>
                    <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.die_method)}</td>
                    <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.production_mode)}</td>
                    <td class="px-2 py-2 text-[#8E8E93] whitespace-nowrap">${esc(fmtPeriodRange(row.effective_year, row.effective_month, row.expiry_year, row.expiry_month))}</td>
                    <td class="${numCell}">${esc(row.process_count)}</td>
                    <td class="px-1 py-2 text-center">
                        <button type="button"
                                class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                                data-action="detail" data-id="${row.id}" title="查看详情" aria-label="查看详情">
                            ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    async showDetail(partId) {
        try {
            const res = await HttpClient.get(`/api/stamping/die/parts/${partId}`);
            this.renderDrawer(res.data);
            this.openDrawer();
        } catch (error) {
            showToast(error.message || '加载详情失败', 'error');
        }
    },

    renderDrawer(part) {
        const content = document.getElementById('dieDrawerContent');
        if (!content || !part) return;
        const num = 'px-2 py-1.5 text-right font-mono text-[10px] tabular-nums text-[#8E8E93]';
        const processes = part.processes || [];
        const processRows = processes.map((proc) => {
            const dim = [proc.die_length, proc.die_width, proc.die_height]
                .map(dieDimMm)
                .join(' × ');
            const ratioCell = this.canUpdate
                ? `<input data-ratio-id="${proc.id}" value="${esc(proc.alloc_ratio)}"
                          class="w-16 h-7 px-2 text-right font-mono text-[10px] bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] focus:outline-none focus:border-[#ff5252]">
                   <button type="button" class="ml-1 text-[10px] text-[#9e9e9e] hover:text-white" data-save-ratio="${proc.id}">保存</button>`
                : `<span class="font-mono text-[10px] text-[#C8C8D0]">${esc(proc.alloc_ratio)}</span>`;
            return `<tr class="border-b border-[#141418]">
                <td class="px-2 py-1.5 text-[#F0F0F2] font-semibold">${esc(proc.process_seq)}</td>
                <td class="px-2 py-1.5 text-[#8E8E93]">${esc(proc.process_code)}</td>
                <td class="px-2 py-1.5 font-mono text-[10px] text-[#F0F0F2]">${esc(proc.die_number)}</td>
                <td class="${num}">${esc(proc.die_sets)}</td>
                <td class="px-2 py-1.5 font-mono text-[10px] text-[#C8C8D0]">${esc(dim)}</td>
                <td class="${num}">${esc(proc.hollow_factor)}</td>
                <td class="${num}">${esc(proc.estimated_weight_t)}</td>
                <td class="${num}">${esc(proc.tonnage)}</td>
                <td class="px-2 py-1.5">${ratioCell}</td>
            </tr>`;
        }).join('');
        content.innerHTML = `
            <div class="mb-4">
                <div class="text-[16px] font-bold text-[#F0F0F2] font-mono tracking-[0.12em]">${esc(shortPartNumber(part.part_number) || part.part_number)}</div>
                <div class="text-[10px] font-mono text-[#3A3A42] mt-0.5">${esc(part.part_number)}</div>
                <div class="text-[11px] text-[#555555] mt-0.5">${esc(part.part_name)}</div>
                <div class="text-[10px] text-[#555555] mt-1">${esc(part.location)} · ${esc(part.vehicle_model)}</div>
                <div class="text-[10px] text-[#9e9e9e] mt-1">${esc(fmtPeriodRange(part.effective_year, part.effective_month, part.expiry_year, part.expiry_month))}</div>
            </div>
            ${this.canUpdate ? `<div class="mb-4">${periodEditorHtml('diePeriod')}
                <button type="button" id="dieSavePeriodBtn"
                        class="mt-2 inline-flex items-center h-7 px-3 text-[10px] text-[#c8c8c8] border border-[#8a2020] hover:text-white">
                    保存生失效
                </button>
            </div>` : ''}
            <div class="grid grid-cols-3 gap-3 text-[11px] mb-5">
                <div class="bg-[#111111] border border-[#222222] p-3">
                    <span class="text-[9px] tracking-wider text-[#555555]">模具类型</span>
                    <div class="text-[#F0F0F2] mt-1">${esc(part.die_type)}</div>
                </div>
                <div class="bg-[#111111] border border-[#222222] p-3">
                    <span class="text-[9px] tracking-wider text-[#555555]">模具方式</span>
                    <div class="text-[#F0F0F2] mt-1">${esc(part.die_method)}</div>
                </div>
                <div class="bg-[#111111] border border-[#222222] p-3">
                    <span class="text-[9px] tracking-wider text-[#555555]">生产方式</span>
                    <div class="text-[#F0F0F2] mt-1">${esc(part.production_mode)}</div>
                </div>
                <div class="bg-[#111111] border border-[#222222] p-3">
                    <span class="text-[9px] tracking-wider text-[#555555]">端拾器</span>
                    <div class="text-[#C8C8D0] mt-1">${esc(part.needs_end_effector)}</div>
                </div>
                <div class="bg-[#111111] border border-[#222222] p-3">
                    <span class="text-[9px] tracking-wider text-[#555555]">零件等级</span>
                    <div class="text-[#C8C8D0] mt-1">${esc(part.part_grade)}</div>
                </div>
                <div class="bg-[#1A080A] border border-[#FF1E27]/20 p-3">
                    <span class="text-[9px] tracking-wider text-[#FF1E27]/80">重量小计 (T)</span>
                    <div class="text-[#FF1E27] font-mono font-bold mt-1 tabular-nums">${esc(part.estimated_weight_subtotal_t)}</div>
                </div>
            </div>
            <p class="text-[9px] tracking-[0.08em] text-[#555555] mb-2">各工序模具</p>
            <div class="overflow-x-auto">
            <table class="w-full border-collapse min-w-[720px]">
                <thead>
                    <tr class="border-b border-[#17171C] text-[9px] text-[#555555]">
                        <th class="px-2 py-1 text-left">工序名称</th>
                        <th class="px-2 py-1 text-left">工序</th>
                        <th class="px-2 py-1 text-left">模具编号</th>
                        <th class="px-2 py-1 text-right">套数</th>
                        <th class="px-2 py-1 text-left">模具长×宽×高</th>
                        <th class="px-2 py-1 text-right">掏空系数</th>
                        <th class="px-2 py-1 text-right">预估重量 (T)</th>
                        <th class="px-2 py-1 text-right">吨位</th>
                        <th class="px-2 py-1 text-left">分摊比例</th>
                    </tr>
                </thead>
                <tbody>${processRows || '<tr><td colspan="9" class="px-2 py-4 text-[#555555] text-center">无模具工序</td></tr>'}</tbody>
            </table>
            </div>
        `;
        content.querySelectorAll('button[data-save-ratio]').forEach((btn) => {
            btn.addEventListener('click', () => this.saveRatio(Number(btn.getAttribute('data-save-ratio')), part.id));
        });
        if (this.canUpdate) {
            fillYearMonthSelects(
                'diePeriod',
                part.effective_year,
                part.effective_month,
                part.expiry_year,
                part.expiry_month,
            );
            document.getElementById('dieSavePeriodBtn')?.addEventListener('click', () => {
                this.savePeriod(part.id);
            });
        }
    },

    async savePeriod(partId) {
        const period = readPeriod('diePeriod');
        if (!period) return;
        try {
            await HttpClient.patch(`/api/stamping/die/parts/${partId}/period`, period);
            showToast('已保存生失效', 'success');
            this.loadList(dieState.page);
            this.showDetail(partId);
        } catch (error) {
            showToast(error.message || '保存失败', 'error');
        }
    },

    async saveRatio(processId, partId) {
        const input = document.querySelector(`input[data-ratio-id="${processId}"]`);
        try {
            await HttpClient.patch(`/api/stamping/die/processes/${processId}`, {
                alloc_ratio: input?.value,
            });
            showToast('分摊比例已更新', 'success');
            this.showDetail(partId);
        } catch (error) {
            showToast(error.message || '保存失败', 'error');
        }
    },

    openDrawer() {
        const drawer = document.getElementById('dieDrawer');
        const backdrop = document.getElementById('dieDrawerBackdrop');
        if (!drawer || !backdrop) return;
        drawer.style.display = 'flex';
        backdrop.style.display = 'block';
        requestAnimationFrame(() => drawer.classList.remove('translate-x-full'));
    },

    closeDrawer() {
        const drawer = document.getElementById('dieDrawer');
        const backdrop = document.getElementById('dieDrawerBackdrop');
        if (!drawer) return;
        drawer.classList.add('translate-x-full');
        if (backdrop) backdrop.style.display = 'none';
        drawer.addEventListener('transitionend', () => {
            drawer.style.display = 'none';
        }, { once: true });
    },

    async exportExcel() {
        const scope = this.requireScope('导出');
        if (!scope) return;
        try {
            const { blob, filename } = await HttpClient.download('/api/stamping/die/export', {
                params: this.collectListFilters(),
                defaultFilename: `冲压模具布点工艺清单_${scope.location}_${scope.vehicle_model}.xlsx`,
            });
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
            showToast('已开始下载', 'success');
        } catch (error) {
            if (!error.status) showToast(error.message || '导出失败', 'error');
        }
    },

    async batchDelete() {
        const scope = this.requireScope('删除');
        if (!scope) return;
        const ok = window.confirm(
            `将删除基地「${scope.location}」项目「${scope.vehicle_model}」下全部模具布点数据，不可恢复。确定？`
        );
        if (!ok) return;
        try {
            const res = await HttpClient.post('/api/stamping/die/batch-delete', scope);
            showToast(res.message || '已删除', 'success');
            this.closeDrawer();
            this.loadList(1);
        } catch (error) {
            showToast(error.message || '删除失败', 'error');
        }
    },
};

export const pageConfig = {
    render: dieListTemplate,
    init: () => DieListPage.init(),
};
