/**
 * 成本还原 — 采购对象查询页。
 */

import { can } from '../../../../core/permissions.js?v=15';
import {
    procurementObjectTemplate,
    renderProcurementObjectRows,
} from './template.js?v=1';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=11';
import { bindFilterBar } from '../../../../ui/filter-bar.js?v=6';
import { setSearchBusy } from '../../../../ui/search-busy.js?v=4';

const API = '/api/costing/cost-restore/procurement-objects';

const state = {
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 0,
    vehicles: [],
    ready: false,
    filterBar: null,
};

function fillSelect(id, options, selected) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = selected ?? select.value;
    const empty = select.querySelector('option[value=""]');
    select.innerHTML = '';
    if (empty) select.appendChild(empty);
    options.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === current)) {
        select.value = current;
    }
}

function selectedLocation() {
    return document.getElementById('crpoFilterLocation')?.value || '';
}

function paintVehicles(preferred) {
    const location = selectedLocation();
    const seen = new Set();
    const rows = state.vehicles.filter((item) => {
        if (location && item.location !== location) return false;
        if (seen.has(item.vehicle_model)) return false;
        seen.add(item.vehicle_model);
        return true;
    });
    fillSelect(
        'crpoFilterVehicle',
        rows.map((item) => ({ value: item.vehicle_model, label: item.vehicle_model })),
        preferred,
    );
}

function collectFilters() {
    return {
        location: selectedLocation(),
        year: document.getElementById('crpoFilterYear')?.value || '',
        month: document.getElementById('crpoFilterMonth')?.value || '',
        vehicle_model: document.getElementById('crpoFilterVehicle')?.value || '',
        supplier_name: document.getElementById('crpoFilterSupplier')?.value || '',
    };
}

function requireFilters() {
    const filters = collectFilters();
    if (!filters.location || !filters.year || !filters.month) {
        if (state.ready) showToast('请选择基地、年、月', 'warning');
        return null;
    }
    return filters;
}

function paintScope(filters) {
    const node = document.getElementById('crpoScope');
    if (!node || !filters) return;
    const project = filters.vehicle_model || '全部项目';
    const note = filters.qa_note ? ` · ${filters.qa_note}` : '';
    node.textContent = `${filters.location} · ${filters.year}年${filters.month}月 · ${project}${note}`;
}

function paintTable(items) {
    const body = document.getElementById('crpoTableBody');
    const empty = document.getElementById('crpoEmpty');
    const wrap = document.getElementById('crpoTableWrap');
    const pager = document.getElementById('crpoPager');
    if (body) body.innerHTML = renderProcurementObjectRows(items);
    const hasRows = items.length > 0;
    empty?.classList.toggle('hidden', hasRows);
    wrap?.classList.toggle('hidden', !hasRows);
    pager?.classList.toggle('hidden', state.total === 0);
    const info = document.getElementById('crpoPageInfo');
    if (info) {
        const objectCount = new Set(items.map((item) => item.object_id)).size;
        info.textContent = state.total
            ? `共 ${state.total} 个采购对象，本页 ${objectCount} 个`
            : '';
    }
    paintPagination('crpoPagination', state.page, state.totalPages);
}

async function loadList(page) {
    const filters = requireFilters();
    if (!filters) return;
    state.page = page;
    setSearchBusy('crpoBtnSearch', true);
    document.getElementById('crpoLoading')?.classList.remove('hidden');
    try {
        const res = await HttpClient.get(API, {
            params: {
                location: filters.location,
                year: filters.year,
                month: filters.month,
                vehicle_model: filters.vehicle_model || undefined,
                supplier_name: filters.supplier_name || undefined,
                page: state.page,
                size: state.pageSize,
            },
        });
        const data = res.data || {};
        state.total = data.total || 0;
        state.totalPages = data.total_pages || 0;
        state.page = data.page || page;
        paintScope(data.filters || filters);
        paintTable(data.items || []);
        state.filterBar?.paint();
    } catch (error) {
        paintTable([]);
    } finally {
        setSearchBusy('crpoBtnSearch', false);
        document.getElementById('crpoLoading')?.classList.add('hidden');
    }
}

async function exportWorkbook() {
    if (!can('op:cost-restore-procurement-object:export')) {
        showToast('没有导出权限', 'warning');
        return;
    }
    const filters = requireFilters();
    if (!filters) return;
    const button = document.getElementById('crpoExportBtn');
    if (button) button.disabled = true;
    try {
        const { blob, filename } = await HttpClient.download(`${API}/export`, {
            params: {
                location: filters.location,
                year: filters.year,
                month: filters.month,
                vehicle_model: filters.vehicle_model || undefined,
                supplier_name: filters.supplier_name || undefined,
            },
            defaultFilename: '成本还原-采购对象.xlsx',
        });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
        showToast(`导出成功: ${filename}`, 'success');
    } catch (error) {
        if (!error.status) showToast(error.message || '导出失败', 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function loadDefaults() {
    const res = await HttpClient.get(`${API}/defaults`);
    const data = res.data || {};
    state.vehicles = data.vehicle_models || [];
    const yearNow = new Date().getFullYear();
    const years = [];
    for (let year = 2020; year <= Math.max(yearNow, data.year || yearNow); year += 1) {
        years.push({ value: String(year), label: `${year}年` });
    }
    const months = Array.from({ length: 12 }, (_, index) => {
        const month = index + 1;
        return { value: String(month), label: `${month}月` };
    });
    fillSelect(
        'crpoFilterLocation',
        (data.locations || []).map((name) => ({ value: name, label: name })),
        data.location || '',
    );
    fillSelect('crpoFilterYear', years, data.year ? String(data.year) : '');
    fillSelect('crpoFilterMonth', months, data.month ? String(data.month) : '');
    fillSelect(
        'crpoFilterSupplier',
        (data.suppliers || []).map((name) => ({ value: name, label: name })),
        '',
    );
    paintVehicles(data.vehicle_model || '');
}

function bindPage() {
    state.filterBar = bindFilterBar({
        prefix: 'crpo',
        searchId: 'crpoBtnSearch',
        capsules: [
            { capsuleId: 'crpoCapsuleLocation', fieldId: 'crpoFilterLocation', idleLabel: '基地' },
            {
                capsuleId: 'crpoCapsulePeriod',
                fieldIds: ['crpoFilterYear', 'crpoFilterMonth'],
                idleLabel: '年月',
                display: () => {
                    const year = document.getElementById('crpoFilterYear')?.value;
                    const month = document.getElementById('crpoFilterMonth')?.value;
                    return year && month ? `${year}年${month}月` : '';
                },
            },
            { capsuleId: 'crpoCapsuleVehicle', fieldId: 'crpoFilterVehicle', idleLabel: '全部项目' },
            { capsuleId: 'crpoCapsuleSupplier', fieldId: 'crpoFilterSupplier', idleLabel: '全部供应商' },
        ],
    });
    bindPagination({
        selectId: 'crpoPageSize',
        buttonsId: 'crpoPagination',
        getSize: () => state.pageSize,
        setSize: (size) => {
            state.pageSize = size;
        },
        onPage: (page) => loadList(page),
    });
    document.getElementById('crpoBtnSearch')?.addEventListener('click', () => loadList(1));
    document.getElementById('crpoFilterLocation')?.addEventListener('change', () => {
        paintVehicles('');
        state.filterBar?.paint();
    });
    document.getElementById('crpoExportBtn')?.addEventListener('click', exportWorkbook);
    if (!can('op:cost-restore-procurement-object:export')) {
        document.getElementById('crpoExportBtn')?.classList.add('hidden');
    }
}

function destroy() {
    state.filterBar?.unbind();
    state.filterBar = null;
    state.ready = false;
}

async function init() {
    bindPage();
    try {
        await loadDefaults();
        state.ready = true;
        state.filterBar?.paint();
        if (selectedLocation() && document.getElementById('crpoFilterYear')?.value) {
            await loadList(1);
        }
    } catch (error) {
        showToast(error.message || '读取默认条件失败', 'error');
    }
}

export const pageConfig = {
    render: procurementObjectTemplate,
    init,
    destroy,
};
