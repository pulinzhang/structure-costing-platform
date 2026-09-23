/**
 * 操作日志 — 对接 /api/settings/logs，筛选项来自权限目录
 */

import { logsTemplate, renderTableRows } from './template.js?v=20';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../ui/page-size.js?v=6';
import { setSearchBusy } from '../../../ui/search-busy.js?v=4';

const logsState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    username: '',
    menuCode: '',
    permissionCode: '',
    success: '',
    createdFrom: '',
    createdTo: '',
    isLoading: false,
    menus: [],
    operations: [],
    catalogByCode: {},
};

const API_BASE = '/api/settings/logs';

function init() {
    bindEvents();
    bindPagination({
        selectId: 'logsPageSize',
        buttonsId: 'paginationBtns',
        getSize: () => logsState.pageSize,
        setSize: (size) => {
            logsState.pageSize = size;
        },
        onPage: (page) => loadData(page),
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
        menuCode: document.getElementById('filterMenu')?.value || '',
        permissionCode: document.getElementById('filterPermission')?.value || '',
        success: document.getElementById('filterSuccess')?.value || '',
        createdFrom: document.getElementById('filterCreatedFrom')?.value || '',
        createdTo: document.getElementById('filterCreatedTo')?.value || '',
    };
}

function applyFiltersToState() {
    const filters = collectFilters();
    logsState.username = filters.username;
    logsState.menuCode = filters.menuCode;
    logsState.permissionCode = filters.permissionCode;
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
    if (logsState.menuCode) params.menu_code = logsState.menuCode;
    if (logsState.permissionCode) params.permission_code = logsState.permissionCode;
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
    return value.length === 16 ? `${value}:00` : value;
}

function fillCatalogFilters() {
    const menuSelect = document.getElementById('filterMenu');
    if (menuSelect) {
        const options = ['<option value="">全部功能</option>']
            .concat((logsState.menus || []).map((item) => {
                const selected = logsState.menuCode === item.code ? ' selected' : '';
                return `<option value="${esc(item.code)}"${selected}>${esc(item.breadcrumb || item.label)}</option>`;
            }));
        menuSelect.innerHTML = options.join('');
    }
    fillPermissionOptions();
}

function fillPermissionOptions() {
    const select = document.getElementById('filterPermission');
    if (!select) return;
    const menuCode = logsState.menuCode;
    const selectedMenu = (logsState.menus || []).find((item) => item.code === menuCode);
    const menuBreadcrumb = selectedMenu ? (selectedMenu.breadcrumb || selectedMenu.label) : '';
    const ops = (logsState.operations || []).filter((item) => {
        if (!menuCode) return true;
        const breadcrumb = item.breadcrumb || '';
        return breadcrumb === menuBreadcrumb || breadcrumb.startsWith(`${menuBreadcrumb} / `);
    });
    const options = ['<option value="">全部动作</option>']
        .concat(ops.map((item) => {
            const selected = logsState.permissionCode === item.code ? ' selected' : '';
            let label = item.label;
            if (!menuCode) {
                label = item.breadcrumb || item.label;
            } else if (menuBreadcrumb && item.breadcrumb && item.breadcrumb.startsWith(`${menuBreadcrumb} / `)) {
                label = item.breadcrumb.slice(menuBreadcrumb.length + 3);
            }
            return `<option value="${esc(item.code)}"${selected}>${esc(label)}</option>`;
        }));
    select.innerHTML = options.join('');
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function applyCatalogOptions(filters) {
    if (!filters) return;
    logsState.menus = filters.menus || [];
    logsState.operations = filters.operations || [];
    const byCode = {};
    (logsState.operations || []).forEach((item) => {
        byCode[item.code] = item;
    });
    logsState.catalogByCode = byCode;
    fillCatalogFilters();
}

async function loadData(page = 1) {
    if (logsState.isLoading) return;
    logsState.isLoading = true;
    setSearchBusy('btnFilter', true);

    const tableBody = document.getElementById('logsTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCountPagination = document.getElementById('totalCountPagination');

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
            applyCatalogOptions(pageResult.filters);
        }

        if (tableBody) {
            if (logsState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(logsState.records, logsState.catalogByCode);
            }
        }

        if (totalCountPagination) {
            totalCountPagination.textContent = `共 ${logsState.total} 条`;
        }
        paintPagination('paginationBtns', logsState.page, logsState.totalPages);
    } catch (error) {
        console.error('加载操作日志失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-ink-muted text-xs">
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


function bindEvents() {
    document.getElementById('btnFilter')?.addEventListener('click', () => {
        applyFiltersToState();
        loadData(1);
    });

    document.getElementById('btnResetFilter')?.addEventListener('click', () => {
        ['filterUsername', 'filterMenu', 'filterPermission', 'filterSuccess', 'filterCreatedFrom', 'filterCreatedTo']
            .forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
        applyFiltersToState();
        fillPermissionOptions();
        loadData(1);
    });

    document.getElementById('filterUsername')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            applyFiltersToState();
            loadData(1);
        }
    });

    document.getElementById('filterMenu')?.addEventListener('change', () => {
        logsState.menuCode = document.getElementById('filterMenu')?.value || '';
        logsState.permissionCode = '';
        const perm = document.getElementById('filterPermission');
        if (perm) perm.value = '';
        fillPermissionOptions();
        applyFiltersToState();
        loadData(1);
    });

    ['filterPermission', 'filterSuccess', 'filterCreatedFrom', 'filterCreatedTo'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            applyFiltersToState();
            loadData(1);
        });
    });

    document.getElementById('btnExportLogs')?.addEventListener('click', exportLogs);
}

async function exportLogs() {
    applyFiltersToState();
    const btn = document.getElementById('btnExportLogs');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-3 h-3 border border-danger border-t-transparent rounded-full animate-spin"></div>
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
