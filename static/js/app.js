/**
 * 结构件自动核价平台 - SPA 主应用
 *
 * 架构说明：
 * - 采用关注点分离（SoC）原则
 * - app.js / main.js : 入口（HTML 直接加载；根目录只留这两份）
 * - core/            : 权限等横切
 * - domain/          : 跨页领域展示（零件身份、耗时）
 * - ui/              : HUD 原语 classes.js + 可复用控件
 * - features/        : 功能模块（template.js + index.js）
 * - llm-assistant/   : 采购助理
 * - vendor/          : 第三方
 *
 * 缓存说明：壳层子模块走裸路径依赖图，业务页在进入路由时再 import()。
 * 由 index.html 中 <script src="app.js?v=…"> 的 query 串驱动入口刷新；
 * 每次脚本更新后需要同步递增 ?v= 版本号。页面模块的 ?v= 写在 pageLoaders 里。
 */

import { installConfirmDialog } from './ui/confirm-dialog.js?v=6';
import { installDeleteErrorDialog } from './ui/error-dialog.js?v=16';
import { bindCurrentRowOnOps } from './ui/table-row.js?v=3';
import { installRecordLists } from './ui/record-list.js?v=7';
import { bindHudSelects, closeHudSelectMenu } from './ui/hud-select.js?v=1';
import { pageMeta } from './features/index.js?v=56';

// 页面导入（路径与 index.html 菜单树 / features 目录对齐）
import { getUserSession, initUserMenu, startTokenHeartbeat, updateUserSession } from './features/login/index.js?v=22';
import {
    applySidebarPermissions,
    canAccessPage,
    fallbackPageName,
} from './core/permissions.js?v=15';
import { pageLoadingHtml, pageNoticeHtml } from './ui/page-loading.js?v=1';

const LLM_BOOT_URL = './llm-assistant/boot.js?v=71';

// 页面按路由再加载。版本号留在 import() 地址上，和以前的静态 import 一样用来破缓存。
const pageLoaders = {
    dashboard: () => import('./features/dashboard/index.js?v=27'),
    'stamping-upload': () => import('./features/stamping/process/upload/index.js?v=80'),
    'stamping-parts': () => import('./features/stamping/process/parts/index.js?v=90'),
    'stamping-die-upload': () => import('./features/stamping/die/upload/index.js?v=33'),
    'stamping-die-list': () => import('./features/stamping/die/list/index.js?v=43'),
    'stamping-die-unit-price': () => import('./features/stamping/die/unit-price/index.js?v=27'),
    'stamping-die-fee-calc': () => import('./features/stamping/die-fee/calc/index.js?v=35'),
    'stamping-die-fee': () => import('./features/stamping/die-fee/list/index.js?v=44'),
    'stamping-gauge-fee-upload': () => import('./features/stamping/gauge-fee/upload/index.js?v=21'),
    'stamping-gauge-fee': () => import('./features/stamping/gauge-fee/list/index.js?v=36'),
    'stamping-tonnage-upload': () => import('./features/stamping/tonnage/upload/index.js?v=25'),
    'stamping-tonnage': () => import('./features/stamping/tonnage/list/index.js?v=49'),
    'stamping-process-fee-calc': () => import('./features/stamping/process-fee/calc/index.js?v=59'),
    'stamping-process-fee': () => import('./features/stamping/process-fee/list/index.js?v=81'),
    'steel-price-list': () => import('./features/costing/steel-price/list/index.js?v=92'),
    'steel-price-calc': () => import('./features/costing/steel-price/calc/index.js?v=41'),
    'stamping-part-cost-calc': () => import('./features/costing/stamping-part-cost/calc/index.js?v=44'),
    'stamping-part-cost': () => import('./features/costing/stamping-part-cost/list/index.js?v=105'),
    'assembly-cost-calc': () => import('./features/costing/assembly-cost/calc/index.js?v=28'),
    'assembly-cost': () => import('./features/costing/assembly-cost/list/index.js?v=66'),
    'procurement-contract-report': () => import('./features/costing/procurement-contract-report/index.js?v=58'),
    'steel-price-policy-upload': () => import('./features/yishiyiyi/policy/upload/index.js?v=54'),
    'steel-price-policy-download': () => import('./features/yishiyiyi/policy/list/index.js?v=64'),
    'base-price-upload': () => import('./features/yishiyiyi/base-price/upload/index.js?v=65'),
    'base-price-download': () => import('./features/yishiyiyi/base-price/list/index.js?v=55'),
    'steel-grade-category': () => import('./features/masterdata/steel-grade-category/index.js?v=29'),
    'steel-mill': () => import('./features/masterdata/steel-mill/index.js?v=2'),
    'winning-thickness-download': () => import('./features/yishiyiyi/winning-thickness/list/index.js?v=33'),
    'scrap-price': () => import('./features/yishiyiyi/scrap-price/index.js?v=34'),
    'bom-structure': () => import('./features/bom/material/structure/index.js?v=20'),
    'bom-where-used': () => import('./features/bom/material/where-used/index.js?v=25'),
    'bom-viz': () => import('./features/bom/material/viz/index.js?v=44'),
    'bom-upload': () => import('./features/bom/material/upload/index.js?v=35'),
    'bom-material': () => import('./features/bom/material/list/index.js?v=26'),
    'bom-welding-unit-price-upload': () => import('./features/bom/welding-unit-price/upload/index.js?v=31'),
    'bom-welding-unit-price': () => import('./features/bom/welding-unit-price/list/index.js?v=41'),
    'bom-annual-part-price-upload': () => import('./features/bom/annual-part-price/upload/index.js?v=31'),
    'bom-annual-part-price': () => import('./features/bom/annual-part-price/list/index.js?v=42'),
    'bom-packaging-transport-fee-upload': () => import('./features/bom/packaging-transport-fee/upload/index.js?v=23'),
    'bom-packaging-transport-fee': () => import('./features/bom/packaging-transport-fee/list/index.js?v=34'),
    'bom-procurement-object': () => import('./features/bom/procurement-object/generate/index.js?v=26'),
    'bom-procurement-object-list': () => import('./features/bom/procurement-object/list/index.js?v=58'),
    'bom-procurement-object-supplier-upload': () => import('./features/bom/procurement-object/supplier-upload/index.js?v=33'),
    'bom-welding-process-breakdown': () => import('./features/bom/welding-process-breakdown/generate/index.js?v=25'),
    'bom-welding-process-breakdown-list': () => import('./features/bom/welding-process-breakdown/list/index.js?v=69'),
    'bom-welding-fee-calc': () => import('./features/bom/welding-fee/calc/index.js?v=31'),
    'bom-welding-fee-list': () => import('./features/bom/welding-fee/list/index.js?v=39'),
    'engineering-change-upload': () => import('./features/engineering-change/design-change/upload/index.js?v=35'),
    'engineering-change-order-list': () => import('./features/engineering-change/design-change/list/index.js?v=46'),
    'engineering-change-material-upload': () => import('./features/engineering-change/material-change/upload/index.js?v=16'),
    'engineering-change-material-list': () => import('./features/engineering-change/material-change/list/index.js?v=12'),
    costing: () => import('./features/costing/engine/index.js?v=58'),
    'file-trace': () => import('./features/file-trace/index.js?v=31'),
    location: () => import('./features/masterdata/location/index.js?v=25'),
    'vehicle-model-upload': () => import('./features/masterdata/vehicle-model/upload/index.js?v=17'),
    'vehicle-model-list': () => import('./features/masterdata/vehicle-model/list/index.js?v=28'),
    'supplier-upload': () => import('./features/masterdata/supplier/upload/index.js?v=18'),
    'supplier-list': () => import('./features/masterdata/supplier/list/index.js?v=29'),
    settings: () => import('./features/settings/system/index.js?v=38'),
    'settings-users': () => import('./features/settings/users/index.js?v=35'),
    'settings-logs': () => import('./features/settings/logs/index.js?v=28'),
    'settings-profile': () => import('./features/settings/profile/index.js?v=18'),
};

// 未登录禁止进入主应用：不渲染业务页，避免请求 dashboard 等后端
const hasSession = !!getUserSession();
if (!hasSession) {
    window.location.replace('/login');
} else {
    installConfirmDialog();
    installDeleteErrorDialog();
}

/** @type {Map<string, { render: () => string, init: () => void, destroy?: () => void }>} */
const loadedPages = new Map();
let renderSerial = 0;

const DEFAULT_PAGE = 'dashboard';
let currentPageName = null;

// ===== Hash 路由核心 =====

/**
 * 从 URL Hash 中解析页面名，如 #/stamping-parts → stamping-parts
 * 支持带查询串：#/steel-price-list?year=2026 → steel-price-list
 * 旧版 #/login 跳转到独立登录页 /login
 */
function getPageFromHash() {
    const hash = window.location.hash;           // e.g. "#/stamping-parts"
    if (!hash || hash === '#' || hash === '#/') return DEFAULT_PAGE;
    let pageName = hash.replace(/^#\/?/, '') || DEFAULT_PAGE;
    const queryIndex = pageName.indexOf('?');
    if (queryIndex >= 0) {
        pageName = pageName.slice(0, queryIndex);
    }
    pageName = pageName || DEFAULT_PAGE;

    // 登录已拆为独立页面，与主应用壳层无关
    if (pageName === 'login') {
        window.location.replace('/login');
        return null;
    }

    return pageName;
}

/**
 * 导航到指定页面（更新 Hash + 渲染）
 */
function navigateTo(pageName) {
    if (!pageLoaders[pageName]) return;
    window.location.hash = '/' + pageName;
}

/** @type {Map<string, Promise<{ render: () => string, init: () => void, destroy?: () => void }>>} */
const pagePromises = new Map();

function loadPage(pageName) {
    const cached = loadedPages.get(pageName);
    if (cached) return Promise.resolve(cached);
    const pending = pagePromises.get(pageName);
    if (pending) return pending;
    const loader = pageLoaders[pageName];
    if (!loader) return Promise.resolve(null);
    const promise = loader()
        .then((mod) => {
            const page = mod.pageConfig;
            if (!page) {
                throw new Error('页面模块缺少 pageConfig');
            }
            loadedPages.set(pageName, page);
            pagePromises.delete(pageName);
            return page;
        })
        .catch((error) => {
            pagePromises.delete(pageName);
            throw error;
        });
    pagePromises.set(pageName, promise);
    return promise;
}

function destroyPage(pageName) {
    const page = loadedPages.get(pageName);
    if (!page || typeof page.destroy !== 'function') return;
    try {
        page.destroy();
    } catch (error) {
        console.error('页面销毁失败:', error);
    }
}

/**
 * 根据页面名查找对应的菜单链接并高亮
 * 同时展开所有父级子菜单，并关闭其他不相关的菜单
 */
function highlightMenu(pageName) {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    // 1. 先移除所有现有的激活状态和展开状态（仅 Overlay 导航 DOM）
    sidebar.querySelectorAll('.sidebar-nav-link.active, .submenu-link.active').forEach(link => {
        link.classList.remove('active');
    });

    // 2. 关闭所有子菜单和 has-submenu
    sidebar.querySelectorAll('.submenu.show, .submenu-nested.show, .has-submenu.open').forEach(el => {
        el.classList.remove('show', 'open');
    });

    // 3. 查找匹配的链接（支持多级菜单）
    const activeLink = sidebar.querySelector(
        `a.sidebar-nav-link[data-page="${pageName}"], a.submenu-link[data-page="${pageName}"]`
    );

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
 * 渲染面包屑：核价 // … // 当前页
 * pageMeta.breadcrumb 为路径段数组（不含品牌根）
 */
function renderBreadcrumb(pageName, meta) {
    const list = document.getElementById('breadcrumbList');
    if (!list) return;

    const segments = Array.isArray(meta.breadcrumb)
        ? meta.breadcrumb
        : String(meta.breadcrumb || pageName).split(/\s*\/\s*/).filter(Boolean);

    const brand = `
        <li>
            <span class="breadcrumb-brand-badge">
                <span class="w-1.5 h-1.5 rounded-full bg-brand shadow-[0_0_6px_rgb(var(--brabus-red))]"></span>
                核价
            </span>
        </li>
    `;

    const trail = segments.map((label, index) => {
        const isLast = index === segments.length - 1;
        const sep = '<li class="breadcrumb-sep" aria-hidden="true">//</li>';

        if (isLast) {
            return `${sep}<li class="breadcrumb-item active" aria-current="page" id="breadcrumbItem"><span>${esc(label)}</span></li>`;
        }
        return `${sep}<li class="breadcrumb-item"><span>${esc(label)}</span></li>`;
    }).join('');

    list.innerHTML = brand + trail;
}

/**
 * 渲染页面（仅渲染，不改 Hash）
 */
async function renderPage(pageName) {
    if (!pageName) return;

    const content = document.getElementById('pageContent');
    const targetPage = pageName;
    if (!pageLoaders[targetPage]) {
        if (content) {
            content.innerHTML = '<div class="text-center text-ink-dim py-12">页面不存在</div>';
        }
        return;
    }

    if (!canAccessPage(targetPage)) {
        const fallback = fallbackPageName();
        if (fallback !== targetPage && pageLoaders[fallback]) {
            if (typeof showToast === 'function') {
                showToast('无访问权限', 'warning');
            }
            window.location.hash = '/' + fallback;
            return;
        }
        if (content) {
            content.innerHTML = '<div class="text-center text-ink-dim py-12">无访问权限</div>';
        }
        return;
    }

    const serial = ++renderSerial;
    if (currentPageName) {
        destroyPage(currentPageName);
        currentPageName = null;
    }

    const alreadyLoaded = loadedPages.has(targetPage);
    if (!alreadyLoaded && content) {
        content.innerHTML = pageLoadingHtml();
    }

    let page;
    try {
        page = await loadPage(targetPage);
    } catch (error) {
        console.error('加载页面模块失败:', error);
        if (serial !== renderSerial) return;
        if (content) content.innerHTML = pageNoticeHtml('页面加载失败');
        return;
    }
    if (serial !== renderSerial || !page) return;

    closeHudSelectMenu();

    const title = document.getElementById('pageTitle');
    const topActions = document.getElementById('topActions');

    highlightMenu(targetPage);

    const meta = pageMeta[targetPage] || { title: targetPage, breadcrumb: [targetPage] };
    if (title) title.textContent = meta.title;
    renderBreadcrumb(targetPage, meta);
    if (topActions) topActions.innerHTML = '';

    try {
        if (content) content.innerHTML = page.render();
        page.init();
        currentPageName = targetPage;
    } catch (error) {
        console.error('渲染页面失败:', error);
        currentPageName = null;
        if (content) {
            content.innerHTML = `<div class="p-4 bg-app-deep border border-line text-brand">加载失败: ${esc(error.message)}</div>`;
        }
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
    if (!hasSession) return;
    // 支持所有带 data-page 的链接（一级、二级、三级菜单）
    const link = e.target.closest('a[data-page]');
    if (!link) return;
    e.preventDefault();
    const pageName = link.getAttribute('data-page');
    navigateTo(pageName);
});

// 监听 Hash 变化（前进/后退 + navigateTo）
window.addEventListener('hashchange', function() {
    if (!hasSession) return;
    const pageName = getPageFromHash();
    renderPage(pageName);
});

// Global Menu → Compact Overlay Menu（复用 #sidebar 菜单 DOM）
document.addEventListener('DOMContentLoaded', function() {
    if (!hasSession) return;
    bindCurrentRowOnOps(document);
    bindHudSelects();
    installRecordLists();

    const sidebar         = document.getElementById('sidebar');
    const sidebarToggle   = document.getElementById('sidebarToggle');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    const closeNav = () => {
        if (!sidebar) return;
        const focused = document.activeElement;
        if (focused && sidebar.contains(focused)) {
            if (sidebarToggle) {
                sidebarToggle.focus();
            } else {
                focused.blur();
            }
        }
        sidebar.classList.remove('is-open');
        sidebar.setAttribute('aria-hidden', 'true');
        sidebar.inert = true;
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.remove('is-visible');
            sidebarBackdrop.setAttribute('aria-hidden', 'true');
        }
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
    };

    const openNav = () => {
        if (!sidebar) return;
        sidebar.inert = false;
        sidebar.classList.add('is-open');
        sidebar.setAttribute('aria-hidden', 'false');
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.add('is-visible');
            sidebarBackdrop.setAttribute('aria-hidden', 'false');
        }
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'true');
    };

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            if (sidebar.classList.contains('is-open')) {
                closeNav();
            } else {
                openNav();
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', closeNav);
    }

    // 选择具体页面后关闭 Overlay（子菜单展开不关闭）
    document.querySelectorAll('.sidebar a[data-page]').forEach(link => {
        link.addEventListener('click', () => closeNav());
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeNav();
    });

    document.querySelectorAll('[data-submenu-toggle]').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const submenuId = this.getAttribute('data-submenu-toggle');
            const submenu = document.getElementById(submenuId);
            const parent = this.closest('.has-submenu');
            if (!submenu || !parent) return;

            const isOpen = parent.classList.contains('open');

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

    // 顶栏用户头像菜单 + token 探活（不续期）
    initUserMenu();
    startTokenHeartbeat();

    // 本地 session 已有权限，先画当前页。me 在后台对账。
    applySidebarPermissions();
    initRouter();
    const assistantModule = import(LLM_BOOT_URL);

    HttpClient.get('/api/auth/me')
        .then((res) => {
            const user = res?.data;
            if (!user) return;
            updateUserSession({
                is_admin: user.is_admin === true,
                permissions: Array.isArray(user.permissions) ? user.permissions : [],
                real_name: user.real_name,
                username: user.username,
                avatar: user.avatar,
                department: user.department,
                email: user.email,
            });
        })
        .catch(() => {})
        .finally(() => {
            applySidebarPermissions();
            const pageName = currentPageName || getPageFromHash();
            if (pageName && !canAccessPage(pageName)) {
                const fallback = fallbackPageName();
                if (fallback !== pageName && pageLoaders[fallback]) {
                    if (typeof showToast === 'function') {
                        showToast('无访问权限', 'warning');
                    }
                    window.location.hash = '/' + fallback;
                }
            }
            assistantModule
                .then((mod) => mod.bootLlmAssistant())
                .catch((error) => {
                    console.error('采购助理加载失败:', error);
                });
        });
});
