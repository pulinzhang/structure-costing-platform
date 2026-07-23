/**
 * 汽车冲压件自动核价平台 - SPA 主应用
 *
 * 架构说明：
 * - 采用关注点分离（SoC）原则
 * - features/      : 功能模块（每个功能一个子目录）
 *   ├── template.js : HTML 模板函数
 *   └── index.js    : 页面逻辑模块
 * - ui/            : 可复用 UI 组件
 * - app.js         : SPA 核心（Hash 路由、渲染、页面注册）
 */

import { pageMeta } from './features/index.js';

// 页面导入
import { pageConfig as dashboardPage }      from './features/dashboard/index.js';
import { pageConfig as stampingUploadPage } from './features/stamping/upload/index.js';
import { pageConfig as stampingPartsPage }  from './features/stamping/parts/index.js';
import { pageConfig as costingPage }        from './features/costing/index.js';
import { pageConfig as quotationPage }      from './features/quotation/index.js';
import { pageConfig as settingsPage }        from './features/settings/index.js';

// ===== 页面注册 =====
const pages = {
    dashboard:       dashboardPage,
    'stamping-upload': stampingUploadPage,
    'stamping-parts': stampingPartsPage,
    costing:         costingPage,
    quotation:       quotationPage,
    settings:        settingsPage,
};

const DEFAULT_PAGE = 'dashboard';

// ===== Hash 路由核心 =====

/**
 * 从 URL Hash 中解析页面名，如 #/stamping-parts → stamping-parts
 */
function getPageFromHash() {
    const hash = window.location.hash;           // e.g. "#/stamping-parts"
    if (!hash || hash === '#' || hash === '#/') return DEFAULT_PAGE;
    return hash.replace(/^#\/?/, '') || DEFAULT_PAGE;
}

/**
 * 导航到指定页面（更新 Hash + 渲染）
 */
function navigateTo(pageName) {
    if (!pages[pageName]) return;
    window.location.hash = '/' + pageName;
}

/**
 * 渲染页面（仅渲染，不改 Hash）
 */
function renderPage(pageName) {
    const page = pages[pageName];
    if (!page) {
        document.getElementById('pageContent').innerHTML =
            '<div class="text-center text-[#616161] py-12">页面不存在</div>';
        return;
    }

    const content = document.getElementById('pageContent');
    const title   = document.getElementById('pageTitle');
    const breadcrumb = document.getElementById('breadcrumbItem');
    const topActions = document.getElementById('topActions');

    // 同步侧边栏高亮
    document.querySelectorAll('.sidebar-nav-link, .submenu-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === pageName) {
            link.classList.add('active');
            const parent = link.closest('.submenu');
            if (parent) parent.classList.add('show');
        }
    });

    // 更新标题栏
    const meta = pageMeta[pageName] || { title: pageName, breadcrumb: pageName };
    if (title)      title.textContent = meta.title;
    if (breadcrumb) breadcrumb.textContent = meta.breadcrumb;
    if (topActions)  topActions.innerHTML = '';

    try {
        content.innerHTML = page.render();
        page.init();
    } catch (error) {
        console.error('渲染页面失败:', error);
        content.innerHTML = `<div class="p-4 bg-[#0a0a0a] border border-[#2c2c2c] text-[#d32f2f]">加载失败: ${esc(error.message)}</div>`;
    }
}

/**
 * 路由初始化：根据当前 Hash 渲染页面
 */
function initRouter() {
    const pageName = getPageFromHash();
    renderPage(pageName);
}

// ===== 全局事件 =====

// 点击导航链接 → 改为更新 Hash
document.addEventListener('click', function(e) {
    const link = e.target.closest('a[data-page]');
    if (!link) return;
    e.preventDefault();
    const pageName = link.getAttribute('data-page');
    navigateTo(pageName);
});

// 监听 Hash 变化（前进/后退 + navigateTo）
window.addEventListener('hashchange', function() {
    const pageName = getPageFromHash();
    renderPage(pageName);
});

// 子菜单折叠切换
document.addEventListener('DOMContentLoaded', function() {
    // --- 侧边栏抽屉（响应式：< 1024px） ---
    const sidebar         = document.getElementById('sidebar');
    const sidebarToggle   = document.getElementById('sidebarToggle');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    const closeSidebar = () => {
        if (!sidebar) return;
        sidebar.classList.remove('is-open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('is-visible');
        if (sidebarToggle)   sidebarToggle.setAttribute('aria-expanded', 'false');
    };

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            if (sidebar.classList.contains('is-open')) {
                closeSidebar();
            } else {
                sidebar.classList.add('is-open');
                if (sidebarBackdrop) sidebarBackdrop.classList.add('is-visible');
                sidebarToggle.setAttribute('aria-expanded', 'true');
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', closeSidebar);
    }

    // 点击侧边栏里的导航链接 → 小屏下自动关闭抽屉
    document.querySelectorAll('.sidebar a[data-page]').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth < 1024) closeSidebar();
        });
    });

    // Esc 关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // 窗口拉大到桌面：自动重置抽屉状态
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 1024) closeSidebar();
    });

    document.querySelectorAll('[data-submenu-toggle]').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const submenuId = this.getAttribute('data-submenu-toggle');
            const submenu = document.getElementById(submenuId);
            const parent  = this.closest('.has-submenu');
            if (!submenu || !parent) return;

            const isOpen = submenu.classList.contains('show');

            document.querySelectorAll('.has-submenu.open').forEach(item => {
                if (item !== parent) {
                    item.classList.remove('open');
                    const s = item.querySelector('.submenu');
                    if (s) s.classList.remove('show');
                }
            });

            if (isOpen) {
                parent.classList.remove('open');
                submenu.classList.remove('show');
            } else {
                parent.classList.add('open');
                submenu.classList.add('show');
            }
        });
    });

    // 启动路由
    initRouter();
});
