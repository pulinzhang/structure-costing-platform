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
 *
 * 缓存说明：所有子模块走裸路径依赖图，由 index.html 中 <script src="app.js?v=9">
 * 入口 URL 的 query 串驱动整体刷新；每次脚本更新后需要同步递增 ?v= 版本号。
 */

import { pageMeta } from './features/index.js';

// 页面导入
import { pageConfig as dashboardPage }      from './features/dashboard/index.js';
import { pageConfig as stampingUploadPage } from './features/stamping/upload/index.js';
import { pageConfig as stampingPartsPage }  from './features/stamping/parts/index.js';
import { pageConfig as stampingTonnagePage } from './features/stamping/tonnage/index.js';
import { pageConfig as steelPriceListPage }   from './features/steel-price/list/index.js';
import { pageConfig as steelPricePolicyUploadPage } from './features/steel-price/policy-upload/index.js';
import { pageConfig as steelPricePolicyDownloadPage } from './features/steel-price/policy-download/index.js';
import { pageConfig as basePriceUploadPage } from './features/steel-price/base-price-upload/index.js';
import { pageConfig as basePriceDownloadPage } from './features/steel-price/base-price-download/index.js';
import { pageConfig as costingPage }        from './features/costing/index.js';
import { pageConfig as quotationPage }      from './features/quotation/index.js';
import { pageConfig as settingsPage }       from './features/settings/index.js';

// ===== 页面注册 =====
const pages = {
    dashboard:        dashboardPage,
    'stamping-upload': stampingUploadPage,
    'stamping-parts':  stampingPartsPage,
    'stamping-tonnage': stampingTonnagePage,
    'steel-price-list': steelPriceListPage,
    'steel-price-policy-upload': steelPricePolicyUploadPage,
    'steel-price-policy-download': steelPricePolicyDownloadPage,
    'base-price-upload': basePriceUploadPage,
    'base-price-download': basePriceDownloadPage,
    costing:          costingPage,
    quotation:        quotationPage,
    settings:         settingsPage,
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
 * 根据页面名查找对应的菜单链接并高亮
 * 同时展开所有父级子菜单，并关闭其他不相关的菜单
 */
function highlightMenu(pageName) {
    // 1. 先移除所有现有的激活状态和展开状态
    document.querySelectorAll('.sidebar-nav-link.active, .submenu-link.active').forEach(link => {
        link.classList.remove('active');
    });

    // 2. 关闭所有子菜单和 has-submenu
    document.querySelectorAll('.submenu.show, .submenu-nested.show, .has-submenu.open').forEach(el => {
        el.classList.remove('show', 'open');
    });

    // 3. 查找匹配的链接（支持多级菜单）
    const selector = `a[data-page="${pageName}"]`;
    const activeLink = document.querySelector(selector);

    if (activeLink) {
        activeLink.classList.add('active');

        // 4. 展开当前链接的所有父级子菜单（包括 .submenu 和 .submenu-nested）
        let parent = activeLink.closest('.submenu, .submenu-nested');
        while (parent) {
            parent.classList.add('show');
            // 找到父级的 has-submenu 并添加 open
            const hasSubmenu = parent.closest('.has-submenu');
            if (hasSubmenu) {
                hasSubmenu.classList.add('open');
            }
            // 继续向上查找父级子菜单
            parent = parent.parentElement?.closest('.submenu, .submenu-nested');
        }
    }
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

    // 同步侧边栏高亮（支持多级菜单自动展开）
    highlightMenu(pageName);

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

// 点击导航链接 → 改为更新 Hash（支持所有 data-page 链接）
document.addEventListener('click', function(e) {
    // 支持所有带 data-page 的链接（一级、二级、三级菜单）
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
            // 找到最近的 has-submenu 父级（可能是 .sidebar-nav-item 或 .submenu-item）
            const parent = this.closest('.has-submenu');
            if (!submenu || !parent) return;

            const isOpen = parent.classList.contains('open');

            // 只关闭同一级别的已打开菜单（不包括嵌套的同级菜单）
            const siblings = parent.parentElement.querySelectorAll(':scope > .has-submenu.open');
            siblings.forEach(item => {
                if (item !== parent) {
                    item.classList.remove('open');
                    const s = item.querySelector(':scope > .submenu');
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
