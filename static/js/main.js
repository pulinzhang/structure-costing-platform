/**
 * 汽车冲压件自动核价平台
 * 主 JavaScript 文件
 * 遵循 docs/front-end.mdc 规范：仅使用 Tailwind 类名
 */

// 全局配置
const AppConfig = {
    debug: true,
    htmxTimeout: 30000,
};

// HTMX 全局配置
if (typeof htmx !== 'undefined') {
    htmx.config.timeout = AppConfig.htmxTimeout;

    // HTMX 事件处理
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        showLoading();
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        hideLoading();
    });

    document.body.addEventListener('htmx:error', function(evt) {
        hideLoading();
        showToast('请求失败，请重试', 'error');
    });

    document.body.addEventListener('htmx:responseError', function(evt) {
        hideLoading();
        showToast('服务器错误，请稍后重试', 'error');
    });
}

// ===== 加载状态管理 =====
let loadingCount = 0;

function showLoading() {
    loadingCount++;
    let overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(overlay);
    }
    overlay.style.display = 'flex';
}

function hideLoading() {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

// ===== Toast 通知（Tailwind 风格） =====
function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();

    // Tailwind 色彩映射
    const colorMap = {
        success: 'bg-green-600',
        danger:  'bg-red-600',
        warning: 'bg-amber-600',
        info:    'bg-sky-600',
        error:   'bg-red-600',
    };
    const bgClass = colorMap[type] || 'bg-slate-600';

    const toast = document.createElement('div');
    toast.className = `flex items-center justify-between gap-3 ${bgClass} text-white px-4 py-3 rounded-md shadow-lg`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <span class="text-sm font-medium">${escapeHtml(message)}</span>
        <button type="button" class="text-white/80 hover:text-white transition-colors" onclick="this.closest('[role=alert]').remove()">
            <i class="bi bi-x-lg"></i>
        </button>
    `;

    toastContainer.appendChild(toast);

    // 自动移除
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container fixed top-4 right-4 flex flex-col gap-2';
        document.body.appendChild(container);
    }
    return container;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ===== HttpClient =====
const HttpClient = (() => {
    const DEFAULT_TIMEOUT = 30000;

    let pendingRequests = 0;

    function trackStart() {
        pendingRequests++;
        showLoading();
    }

    function trackEnd() {
        pendingRequests = Math.max(0, pendingRequests - 1);
        if (pendingRequests === 0) hideLoading();
    }

    function buildUrl(url, params) {
        if (!params) return url;
        const usp = new URLSearchParams();
        for (const [key, value] of Object.entries(params)) {
            if (value === undefined || value === null || value === '') continue;
            usp.append(key, String(value));
        }
        const qs = usp.toString();
        if (!qs) return url;
        return url.includes('?') ? `${url}&${qs}` : `${url}?${qs}`;
    }

    async function parseResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json();
        }
        const text = await response.text();
        try { return JSON.parse(text); } catch { return text; }
    }

    async function request(method, url, { params, body, headers, timeout } = {}) {
        const fullUrl = buildUrl(url, params);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout || DEFAULT_TIMEOUT);

        const init = {
            method,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...(headers || {}),
            },
            signal: controller.signal,
        };

        if (body !== undefined && body !== null) {
            if (body instanceof FormData || body instanceof Blob || body instanceof ArrayBuffer) {
                init.body = body;
            } else {
                init.headers['Content-Type'] = init.headers['Content-Type'] || 'application/json';
                init.body = typeof body === 'string' ? body : JSON.stringify(body);
            }
        }

        trackStart();
        try {
            const response = await fetch(fullUrl, init);
            clearTimeout(timer);
            const data = await parseResponse(response);

            if (data && typeof data === 'object' && 'success' in data) {
                if (data.success) {
                    return { ok: true, status: response.status, data: data.data, message: data.message };
                }
                const msg = data.message || data.detail || '请求失败';
                showToast(msg, 'danger');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            if (!response.ok) {
                const msg = (data && (data.message || data.detail)) || `请求失败 (${response.status})`;
                showToast(msg, 'danger');
                const err = new Error(msg);
                err.status = response.status;
                throw err;
            }

            return { ok: true, status: response.status, data };
        } catch (error) {
            clearTimeout(timer);
            let message = error.message || '网络请求失败';
            if (error.name === 'AbortError') message = '请求超时，请重试';
            if (message !== error.message) {
                showToast(message, 'danger');
            }
            throw error;
        } finally {
            trackEnd();
        }
    }

    return {
        get:    (url, opts) => request('GET',    url, opts),
        post:   (url, body, opts) => request('POST',   url, { ...(opts || {}), body }),
        put:    (url, body, opts) => request('PUT',    url, { ...(opts || {}), body }),
        patch:  (url, body, opts) => request('PATCH',  url, { ...(opts || {}), body }),
        delete: (url, opts) => request('DELETE', url, opts),
    };
})();

// ===== FileUploader（Tailwind 风格预览） =====
class FileUploader {
    constructor(options = {}) {
        this.dropZone = options.dropZone;
        this.inputElement = options.inputElement;
        this.previewElement = options.previewElement;
        this.maxSize = options.maxSize || 50 * 1024 * 1024;
        this.allowedTypes = options.allowedTypes || ['.xlsx', '.xls', '.csv'];

        this.init();
    }

    init() {
        if (this.dropZone) {
            this.setupDragAndDrop();
        }
        if (this.inputElement) {
            this.inputElement.addEventListener('change', (e) => this.handleFileSelect(e));
        }
    }

    setupDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.remove('dragover');
            });
        });

        this.dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.processFiles(files);
        });
    }

    handleFileSelect(event) {
        const files = event.target.files;
        this.processFiles(files);
    }

    processFiles(files) {
        for (const file of files) {
            if (!this.validateFile(file)) {
                continue;
            }
            this.onFileSelected(file);
        }
    }

    validateFile(file) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!this.allowedTypes.includes(ext)) {
            showToast(`不支持的文件类型: ${ext}`, 'warning');
            return false;
        }

        if (file.size > this.maxSize) {
            showToast(`文件过大: ${file.name} (最大 ${this.formatFileSize(this.maxSize)})`, 'warning');
            return false;
        }

        return true;
    }

    onFileSelected(file) {
        console.log('文件已选择:', file.name, this.formatFileSize(file.size));

        if (this.previewElement) {
            this.previewElement.innerHTML = `
                <div class="flex items-center gap-3 p-3 bg-sky-50 border border-sky-200 rounded-md">
                    <i class="bi bi-file-earmark-excel text-2xl text-green-600"></i>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium text-slate-900 truncate">${escapeHtml(file.name)}</div>
                        <div class="text-xs text-slate-500">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
            `;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// ===== 分页（Tailwind 风格） =====
function initPagination(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const {
        totalItems = 0,
        currentPage = 1,
        pageSize = 20,
        onPageChange = () => {}
    } = options;

    const totalPages = Math.ceil(totalItems / pageSize);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<nav class="flex items-center justify-center gap-1">';

    // 上一页
    html += `
        <button class="p-2 rounded-md text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="bi bi-chevron-left"></i>
        </button>
    `;

    // 页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            const isActive = i === currentPage;
            html += `
                <button class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors
                    ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}"
                    data-page="${i}">
                    ${i}
                </button>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<span class="px-2 text-slate-400">...</span>`;
        }
    }

    // 下一页
    html += `
        <button class="p-2 rounded-md text-slate-500 hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <i class="bi bi-chevron-right"></i>
        </button>
    `;

    html += '</nav>';
    container.innerHTML = html;

    // 绑定事件
    container.querySelectorAll('button[data-page]').forEach(btn => {
        btn.addEventListener('click', function() {
            const page = parseInt(this.dataset.page);
            if (!isNaN(page) && !this.disabled) {
                onPageChange(page);
            }
        });
    });
}

// ===== 表格排序（Tailwind 风格） =====
function initTableSort() {
    document.querySelectorAll('th[data-sortable]').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const columnIndex = Array.from(this.parentNode.children).indexOf(this);
            const isAsc = this.classList.contains('sort-asc');

            // 清除所有排序标记
            table.querySelectorAll('th').forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });

            // 排序
            rows.sort((a, b) => {
                const aVal = a.children[columnIndex]?.textContent.trim() || '';
                const bVal = b.children[columnIndex]?.textContent.trim() || '';

                if (isAsc) {
                    return aVal.localeCompare(bVal, 'zh-CN', { numeric: true });
                } else {
                    return bVal.localeCompare(aVal, 'zh-CN', { numeric: true });
                }
            });

            // 重新添加行
            rows.forEach(row => tbody.appendChild(row));

            // 添加排序标记
            this.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
        });
    });
}

// ===== 搜索过滤 =====
function filterTable(tableId, searchInputId) {
    const input = document.getElementById(searchInputId);
    const filter = input.value.toLowerCase();
    const table = document.getElementById(tableId);
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (const row of rows) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    }
}

// ===== 侧边栏子菜单（纯 JS，无 Bootstrap 依赖） =====
function initSidebarSubmenus() {
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
                    if (otherSubmenu) {
                        otherSubmenu.classList.remove('show');
                    }
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
}

// ===== DOM 加载完成后初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    initTableSort();
    initSidebarSubmenus();
});

// ===== 导出全局函数 =====
window.AppConfig = AppConfig;
window.HttpClient = HttpClient;
window.Http = HttpClient;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showToast = showToast;
window.confirmAction = confirmAction;
window.FileUploader = FileUploader;
window.initTableSort = initTableSort;
window.filterTable = filterTable;
window.initPagination = initPagination;
