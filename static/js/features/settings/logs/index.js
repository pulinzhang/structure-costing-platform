/**
 * Operation Logs Page
 * 操作日志 — 对接 /api/settings/logs
 */

import { logsTemplate, renderTableRows, renderPagination } from './template.js?v=1';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../page-size.js?v=2';
import { setSearchBusy } from '../../../search-busy.js?v=1';

const logsState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    username: '',
    module: '',
    action: '',
    method: '',
    success: '',
    createdFrom: '',
    createdTo: '',
    isLoading: false,
    filterOptionsApplied: false,
};

const API_BASE = '/api/settings/logs';

function init() {
    bindEvents();
    bindPageSizeSelect('logsPageSize', {
        getSize: () => logsState.pageSize,
        setSize: (size) => {
            logsState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    const btnExport = document.getElementById('btnExportLogs');
    if (btnExport && typeof can === 'function' && !can('op:settings-logs:export')) {
        btnExport.classList.add('hidden');
    }
    loadData();
}

function collectFilters() {
    return {
        username: (document.getElementById('filterUsername')?.value || '').trim(),
        module: document.getElementById('filterModule')?.value || '',
        action: document.getElementById('filterAction')?.value || '',
        method: document.getElementById('filterMethod')?.value || '',
        success: document.getElementById('filterSuccess')?.value || '',
        createdFrom: document.getElementById('filterCreatedFrom')?.value || '',
        createdTo: document.getElementById('filterCreatedTo')?.value || '',
    };
}

function applyFiltersToState() {
    const filters = collectFilters();
    logsState.username = filters.username;
    logsState.module = filters.module;
    logsState.action = filters.action;
    logsState.method = filters.method;
    logsState.success = filters.success;
    logsState.createdFrom = filters.createdFrom;
    logsState.createdTo = filters.createdTo;
}

function buildQueryParams(page) {
    const params = {
        page,
        size: logsState.pageSize,
    };
    if (logsState.username) params.username = logsState.username;
    if (logsState.module) params.module = logsState.module;
    if (logsState.action) params.action = logsState.action;
    if (logsState.method) params.method = logsState.method;
    if (logsState.success !== '') params.success = logsState.success;
    if (logsState.createdFrom) {
        params.created_from = localDatetimeToIso(logsState.createdFrom);
    }
    if (logsState.createdTo) {
        params.created_to = localDatetimeToIso(logsState.createdTo);
    }
    return params;
}

function localDatetimeToIso(value) {
    if (!value) return undefined;
    // datetime-local → ISO（无时区），供 FastAPI datetime 查询参数解析
    return value.length === 16 ? `${value}:00` : value;
}

function fillSelectOptions(selectId, values, currentValue) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const options = ['<option value="">全部</option>']
        .concat((values || []).map((v) => {
            const selected = currentValue === v ? ' selected' : '';
            return `<option value="${esc(v)}"${selected}>${esc(v)}</option>`;
        }));
    select.innerHTML = options.join('');
}

function applyFilterOptions(filters) {
    if (!filters) return;
    fillSelectOptions('filterModule', filters.modules, logsState.module);
    fillSelectOptions('filterAction', filters.actions, logsState.action);
    fillSelectOptions('filterMethod', filters.methods, logsState.method);
    logsState.filterOptionsApplied = true;
}

async function loadData(page = 1) {
    if (logsState.isLoading) return;
    logsState.isLoading = true;
    setSearchBusy('btnFilter', true);

    const tableBody = document.getElementById('logsTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCountPagination = document.getElementById('totalCountPagination');
    const paginationBtns = document.getElementById('paginationBtns');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const res = await HttpClient.get(API_BASE, { params: buildQueryParams(page) });
        const pageResult = res.data || {};

        logsState.records = pageResult.items || [];
        logsState.total = pageResult.total || 0;
        logsState.page = pageResult.page || page;
        logsState.totalPages = pageResult.total_pages || 1;

        if (pageResult.filters) {
            applyFilterOptions(pageResult.filters);
        }

        if (tableBody) {
            if (logsState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(logsState.records);
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${logsState.total} 条`;
        }
        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(logsState.page, logsState.totalPages);
            bindPaginationEvents();
        }
    } catch (error) {
        console.error('加载操作日志失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
                        加载数据失败，请重试
                    </td>
                </tr>
            `;
        }
        if (!error.status) {
            showToast(error.message || '加载操作日志失败', 'error');
        }
    } finally {
        if (loadingState) loadingState.classList.add('hidden');
        logsState.isLoading = false;
        setSearchBusy('btnFilter', false);
    }
}

function bindPaginationEvents() {
    document.querySelectorAll('#paginationBtns .page-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const page = Number(btn.getAttribute('data-page'));
            if (!Number.isFinite(page) || page < 1) return;
            loadData(page);
        });
    });
}

function bindEvents() {
    const btnFilter = document.getElementById('btnFilter');
    if (btnFilter) {
        btnFilter.addEventListener('click', () => {
            applyFiltersToState();
            loadData(1);
        });
    }

    const btnReset = document.getElementById('btnResetFilter');
    if (btnReset) {
        btnReset.addEventListener('click', () => {
            const username = document.getElementById('filterUsername');
            const module = document.getElementById('filterModule');
            const action = document.getElementById('filterAction');
            const method = document.getElementById('filterMethod');
            const success = document.getElementById('filterSuccess');
            const createdFrom = document.getElementById('filterCreatedFrom');
            const createdTo = document.getElementById('filterCreatedTo');
            if (username) username.value = '';
            if (module) module.value = '';
            if (action) action.value = '';
            if (method) method.value = '';
            if (success) success.value = '';
            if (createdFrom) createdFrom.value = '';
            if (createdTo) createdTo.value = '';
            applyFiltersToState();
            loadData(1);
        });
    }

    const usernameInput = document.getElementById('filterUsername');
    if (usernameInput) {
        usernameInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                applyFiltersToState();
                loadData(1);
            }
        });
    }

    [
        'filterModule',
        'filterAction',
        'filterMethod',
        'filterSuccess',
        'filterCreatedFrom',
        'filterCreatedTo',
    ].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            applyFiltersToState();
            loadData(1);
        });
    });

    const btnExport = document.getElementById('btnExportLogs');
    if (btnExport) {
        btnExport.addEventListener('click', exportLogs);
    }
}

async function exportLogs() {
    applyFiltersToState();
    const btn = document.getElementById('btnExportLogs');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-[#ef5350] border-t-transparent rounded-full animate-spin"></div>
            导出中...
        `;
    }

    try {
        const params = { ...buildQueryParams(1) };
        delete params.page;
        delete params.size;

        const { blob, filename } = await HttpClient.download(`${API_BASE}/export-download`, {
            params,
            defaultFilename: '操作日志导出.xlsx',
        });

        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(url);

        showToast(`导出成功: ${filename}`, 'success');
        // 导出本身会记审计，刷新列表可见新记录
        loadData(logsState.page);
    } catch (error) {
        console.error('导出操作日志失败:', error);
        if (!error.status) {
            showToast(error.message || '导出失败', 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

export const pageConfig = {
    render: logsTemplate,
    init: () => init(),
};
