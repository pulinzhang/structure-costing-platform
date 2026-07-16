/**
 * 汽车冲压件自动核价平台
 * 主 JavaScript 文件
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

// 加载状态管理
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

// Toast 通知
function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
    }
    return container;
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 文件上传处理
class FileUploader {
    constructor(options = {}) {
        this.dropZone = options.dropZone;
        this.inputElement = options.inputElement;
        this.previewElement = options.previewElement;
        this.maxSize = options.maxSize || 50 * 1024 * 1024; // 50MB
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
                <div class="alert alert-info mb-0">
                    <i class="bi bi-file-earmark-excel me-2"></i>
                    <strong>${file.name}</strong>
                    <span class="text-muted ms-2">${this.formatFileSize(file.size)}</span>
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

// 表格排序
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
                const aVal = a.children[columnIndex].textContent.trim();
                const bVal = b.children[columnIndex].textContent.trim();

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

// 搜索过滤
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

// 分页初始化
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

    let html = '<nav><ul class="pagination mb-0">';

    // 上一页
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${currentPage - 1}">&laquo;</a>
    </li>`;

    // 页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }

    // 下一页
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${currentPage + 1}">&raquo;</a>
    </li>`;

    html += '</ul></nav>';
    container.innerHTML = html;

    // 绑定事件
    container.querySelectorAll('.page-link[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.dataset.page);
            if (!isNaN(page)) {
                onPageChange(page);
            }
        });
    });
}

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化表格排序
    initTableSort();

    // 初始化工具提示
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));

    // 初始化弹出框
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(el => new bootstrap.Popover(el));
});

// 导出全局函数
window.AppConfig = AppConfig;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showToast = showToast;
window.confirmAction = confirmAction;
window.FileUploader = FileUploader;
window.initTableSort = initTableSort;
window.filterTable = filterTable;
window.initPagination = initPagination;
