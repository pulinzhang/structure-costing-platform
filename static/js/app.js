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
 * 缓存说明：所有子模块走裸路径依赖图，由 index.html 中 <script src="app.js?v=…">
 * 入口 URL 的 query 串驱动整体刷新；每次脚本更新后需要同步递增 ?v= 版本号。
 */

import { pageMeta } from './features/index.js?v=40';

// 页面导入（路径与 index.html 菜单树 / features 目录对齐）
import { getUserSession, initUserMenu, startTokenHeartbeat, updateUserSession } from './features/login/index.js?v=15';
import {
    applySidebarPermissions,
    canAccessPage,
    fallbackPageName,
} from './permissions.js?v=11';
import { bootLlmAssistant } from './llm-assistant/boot.js?v=29';
import { pageConfig as dashboardPage }      from './features/dashboard/index.js?v=12';
import { pageConfig as stampingUploadPage } from './features/stamping/process/upload/index.js?v=56';
import { pageConfig as stampingPartsPage }  from './features/stamping/process/parts/index.js?v=47';
import { pageConfig as stampingDieUploadPage } from './features/stamping/die/upload/index.js?v=11';
import { pageConfig as stampingDieListPage } from './features/stamping/die/list/index.js?v=11';
import { pageConfig as stampingDieUnitPricePage } from './features/stamping/die/unit-price/index.js?v=8';
import { pageConfig as stampingDieFeeCalcPage } from './features/stamping/die-fee/calc/index.js?v=15';
import { pageConfig as stampingDieFeePage } from './features/stamping/die-fee/list/index.js?v=11';
import { pageConfig as stampingGaugeFeeUploadPage } from './features/stamping/gauge-fee/upload/index.js?v=5';
import { pageConfig as stampingGaugeFeePage } from './features/stamping/gauge-fee/list/index.js?v=11';
import { pageConfig as stampingTonnagePage } from './features/stamping/tonnage/list/index.js?v=26';
import { pageConfig as stampingTonnageUploadPage } from './features/stamping/tonnage/upload/index.js?v=7';
import { pageConfig as stampingProcessFeeCalcPage } from './features/stamping/process-fee/calc/index.js?v=39';
import { pageConfig as stampingProcessFeePage } from './features/stamping/process-fee/list/index.js?v=53';
import { pageConfig as steelPriceListPage }   from './features/costing/steel-price/list/index.js?v=62';
import { pageConfig as steelPriceCalcPage }    from './features/costing/steel-price/calc/index.js?v=25';
import { pageConfig as stampingPartCostCalcPage } from './features/costing/stamping-part-cost/calc/index.js?v=22';
import { pageConfig as stampingPartCostPage } from './features/costing/stamping-part-cost/list/index.js?v=72';
import { pageConfig as assemblyCostCalcPage } from './features/costing/assembly-cost/calc/index.js?v=9';
import { pageConfig as assemblyCostPage } from './features/costing/assembly-cost/list/index.js?v=26';
import { pageConfig as procurementContractReportPage } from './features/costing/procurement-contract-report/index.js?v=15';
import { pageConfig as steelPricePolicyUploadPage } from './features/yishiyiyi/policy/upload/index.js?v=39';
import { pageConfig as steelPricePolicyDownloadPage } from './features/yishiyiyi/policy/list/index.js?v=38';
import { pageConfig as basePriceUploadPage } from './features/yishiyiyi/base-price/upload/index.js?v=40';
import { pageConfig as basePriceDownloadPage } from './features/yishiyiyi/base-price/list/index.js?v=35';
import { pageConfig as winningThicknessDownloadPage } from './features/yishiyiyi/winning-thickness/list/index.js?v=15';
import { pageConfig as steelGradeCategoryPage } from './features/yishiyiyi/steel-grade-category/index.js?v=4';
import { pageConfig as scrapPricePage } from './features/yishiyiyi/scrap-price/index.js?v=21';
import { pageConfig as bomStructurePage }  from './features/bom/material/structure/index.js?v=9';
import { pageConfig as bomVizPage }        from './features/bom/material/viz/index.js?v=29';
import { pageConfig as bomUploadPage }     from './features/bom/material/upload/index.js?v=11';
import { pageConfig as bomMaterialListPage } from './features/bom/material/list/index.js?v=5';
import { pageConfig as bomWeldingUnitPriceUploadPage } from './features/bom/welding-unit-price/upload/index.js?v=11';
import { pageConfig as bomWeldingUnitPricePage } from './features/bom/welding-unit-price/list/index.js?v=18';
import { pageConfig as bomAnnualPartPriceUploadPage } from './features/bom/annual-part-price/upload/index.js?v=14';
import { pageConfig as bomAnnualPartPricePage } from './features/bom/annual-part-price/list/index.js?v=16';
import { pageConfig as bomPackagingTransportFeeUploadPage } from './features/bom/packaging-transport-fee/upload/index.js?v=6';
import { pageConfig as bomPackagingTransportFeePage } from './features/bom/packaging-transport-fee/list/index.js?v=9';
import { pageConfig as bomProcurementObjectGeneratePage } from './features/bom/procurement-object/generate/index.js?v=7';
import { pageConfig as bomProcurementObjectListPage } from './features/bom/procurement-object/list/index.js?v=15';
import { pageConfig as bomProcurementObjectSupplierUploadPage } from './features/bom/procurement-object/supplier-upload/index.js?v=4';
import { pageConfig as bomWeldingProcessBreakdownGeneratePage } from './features/bom/welding-process-breakdown/generate/index.js?v=8';
import { pageConfig as bomWeldingProcessBreakdownListPage } from './features/bom/welding-process-breakdown/list/index.js?v=41';
import { pageConfig as bomWeldingFeeCalcPage } from './features/bom/welding-fee/calc/index.js?v=7';
import { pageConfig as bomWeldingFeeListPage } from './features/bom/welding-fee/list/index.js?v=9';
import { pageConfig as costingPage }        from './features/costing/engine/index.js?v=31';
import { pageConfig as fileTracePage }       from './features/file-trace/index.js?v=8';
import { pageConfig as locationPage }        from './features/masterdata/location/index.js?v=7';
import { pageConfig as vehicleModelUploadPage } from './features/masterdata/vehicle-model/upload/index.js?v=2';
import { pageConfig as vehicleModelListPage } from './features/masterdata/vehicle-model/list/index.js?v=4';
import { pageConfig as supplierUploadPage } from './features/masterdata/supplier/upload/index.js?v=1';
import { pageConfig as supplierListPage } from './features/masterdata/supplier/list/index.js?v=3';
import { pageConfig as settingsPage }       from './features/settings/system/index.js?v=20';
import { pageConfig as settingsUsersPage }  from './features/settings/users/index.js?v=13';
import { pageConfig as settingsLogsPage }   from './features/settings/logs/index.js?v=7';
import { pageConfig as settingsProfilePage } from './features/settings/profile/index.js?v=9';

// 未登录禁止进入主应用：不渲染业务页，避免请求 dashboard 等后端
const hasSession = !!getUserSession();
if (!hasSession) {
    window.location.replace('/login');
}

// ===== 页面注册 =====
const pages = {
    dashboard:        dashboardPage,
    'stamping-upload': stampingUploadPage,
    'stamping-parts':  stampingPartsPage,
    'stamping-die-upload': stampingDieUploadPage,
    'stamping-die-list': stampingDieListPage,
    'stamping-die-unit-price': stampingDieUnitPricePage,
    'stamping-die-fee-calc': stampingDieFeeCalcPage,
    'stamping-die-fee': stampingDieFeePage,
    'stamping-gauge-fee-upload': stampingGaugeFeeUploadPage,
    'stamping-gauge-fee': stampingGaugeFeePage,
    'stamping-tonnage-upload': stampingTonnageUploadPage,
    'stamping-tonnage': stampingTonnagePage,
    'stamping-process-fee-calc': stampingProcessFeeCalcPage,
    'stamping-process-fee': stampingProcessFeePage,
    'steel-price-list': steelPriceListPage,
    'steel-price-calc': steelPriceCalcPage,
    'stamping-part-cost-calc': stampingPartCostCalcPage,
    'stamping-part-cost': stampingPartCostPage,
    'assembly-cost-calc': assemblyCostCalcPage,
    'assembly-cost': assemblyCostPage,
    'procurement-contract-report': procurementContractReportPage,
    'steel-price-policy-upload': steelPricePolicyUploadPage,
    'steel-price-policy-download': steelPricePolicyDownloadPage,
    'base-price-upload': basePriceUploadPage,
    'base-price-download': basePriceDownloadPage,
    'steel-grade-category': steelGradeCategoryPage,
    'winning-thickness-download': winningThicknessDownloadPage,
    'scrap-price': scrapPricePage,
    'bom-structure':  bomStructurePage,
    'bom-viz':        bomVizPage,
    'bom-upload':     bomUploadPage,
    'bom-material':   bomMaterialListPage,
    'bom-welding-unit-price-upload': bomWeldingUnitPriceUploadPage,
    'bom-welding-unit-price': bomWeldingUnitPricePage,
    'bom-annual-part-price-upload': bomAnnualPartPriceUploadPage,
    'bom-annual-part-price': bomAnnualPartPricePage,
    'bom-packaging-transport-fee-upload': bomPackagingTransportFeeUploadPage,
    'bom-packaging-transport-fee': bomPackagingTransportFeePage,
    'bom-procurement-object': bomProcurementObjectGeneratePage,
    'bom-procurement-object-list': bomProcurementObjectListPage,
    'bom-procurement-object-supplier-upload': bomProcurementObjectSupplierUploadPage,
    'bom-welding-process-breakdown': bomWeldingProcessBreakdownGeneratePage,
    'bom-welding-process-breakdown-list': bomWeldingProcessBreakdownListPage,
    'bom-welding-fee-calc': bomWeldingFeeCalcPage,
    'bom-welding-fee-list': bomWeldingFeeListPage,
    costing:          costingPage,
    'file-trace':     fileTracePage,
    location:         locationPage,
    'vehicle-model-upload': vehicleModelUploadPage,
    'vehicle-model-list': vehicleModelListPage,
    'supplier-upload': supplierUploadPage,
    'supplier-list': supplierListPage,
    settings:         settingsPage,
    'settings-users': settingsUsersPage,
    'settings-logs': settingsLogsPage,
    'settings-profile': settingsProfilePage,
};

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

    // 旧 BOM 列表 / Phase A 临时路由 → 产品结构 / 上传
    if (pageName === 'bom') {
        return 'bom-upload';
    }
    if (pageName === 'bom-list') {
        return 'bom-structure';
    }

    if (pageName === 'bom-l0-welding-fee-calc') {
        return 'bom-welding-fee-calc';
    }
    if (pageName === 'bom-l0-welding-fee-list') {
        return 'bom-welding-fee-list';
    }

    if (pageName === 'l0-assembly-cost-calc') {
        return 'assembly-cost-calc';
    }
    if (pageName === 'l0-assembly-cost') {
        return 'assembly-cost';
    }
    if (pageName === 'vehicle-model') {
        return 'vehicle-model-list';
    }
    if (pageName === 'supplier') {
        return 'supplier-list';
    }

    return pageName;
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
    const activeLink = sidebar.querySelector(`a[data-page="${pageName}"]`);

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
 * 渲染面包屑：STAMPING // … // 当前页
 * pageMeta.breadcrumb 为路径段数组（不含品牌根）
 * pageMeta.en 写入当前页 data-en 英文刻度
 */
function renderBreadcrumb(pageName, meta) {
    const list = document.getElementById('breadcrumbList');
    if (!list) return;

    const segments = Array.isArray(meta.breadcrumb)
        ? meta.breadcrumb
        : String(meta.breadcrumb || pageName).split(/\s*\/\s*/).filter(Boolean);

    const enCode = meta.en || 'PAGE_VIEW';
    const brand = `
        <li>
            <span class="breadcrumb-brand-badge">
                <span class="w-1.5 h-1.5 rounded-full bg-[#d32f2f] shadow-[0_0_6px_#d32f2f]"></span>
                STAMPING
            </span>
        </li>
    `;

    const trail = segments.map((label, index) => {
        const isLast = index === segments.length - 1;
        const sep = '<li class="breadcrumb-sep" aria-hidden="true">//</li>';

        if (isLast) {
            return `${sep}<li class="breadcrumb-item active" aria-current="page" id="breadcrumbItem" data-en="${esc(enCode)}">${esc(label)}</li>`;
        }
        return `${sep}<li class="breadcrumb-item">${esc(label)}</li>`;
    }).join('');

    list.innerHTML = brand + trail;
}

/**
 * 渲染页面（仅渲染，不改 Hash）
 */
function renderPage(pageName) {
    if (!pageName) return;

    let targetPage = pageName;
    if (!pages[targetPage]) {
        document.getElementById('pageContent').innerHTML =
            '<div class="text-center text-[#616161] py-12">页面不存在</div>';
        return;
    }

    if (!canAccessPage(targetPage)) {
        const fallback = fallbackPageName();
        if (fallback !== targetPage && pages[fallback]) {
            if (typeof showToast === 'function') {
                showToast('无访问权限', 'warning');
            }
            window.location.hash = '/' + fallback;
            return;
        }
        document.getElementById('pageContent').innerHTML =
            '<div class="text-center text-[#616161] py-12">无访问权限</div>';
        return;
    }

    const page = pages[targetPage];

    // 离开上一页时调用 destroy（停止轮询等），避免后台定时器污染当前页
    if (currentPageName && pages[currentPageName]?.destroy) {
        try {
            pages[currentPageName].destroy();
        } catch (error) {
            console.error('页面销毁失败:', error);
        }
    }

    const content = document.getElementById('pageContent');
    const title   = document.getElementById('pageTitle');
    const topActions = document.getElementById('topActions');

    // 同步导航高亮（Overlay 复用同一套菜单 DOM）
    highlightMenu(targetPage);

    const meta = pageMeta[targetPage] || { title: targetPage, breadcrumb: [targetPage] };
    if (title) title.textContent = meta.title;
    renderBreadcrumb(targetPage, meta);
    if (topActions) topActions.innerHTML = '';

    try {
        content.innerHTML = page.render();
        page.init();
        currentPageName = targetPage;
    } catch (error) {
        console.error('渲染页面失败:', error);
        currentPageName = null;
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

    const sidebar         = document.getElementById('sidebar');
    const sidebarToggle   = document.getElementById('sidebarToggle');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    const closeNav = () => {
        if (!sidebar) return;
        sidebar.classList.remove('is-open');
        sidebar.setAttribute('aria-hidden', 'true');
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.remove('is-visible');
            sidebarBackdrop.setAttribute('aria-hidden', 'true');
        }
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
    };

    const openNav = () => {
        if (!sidebar) return;
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

    // 启动时拉一次 me，刷新权限后再过滤侧栏与路由
    HttpClient.get('/api/auth/me')
        .then((res) => {
            const user = res?.data;
            if (user) {
                updateUserSession({
                    is_admin: user.is_admin === true,
                    permissions: Array.isArray(user.permissions) ? user.permissions : [],
                    real_name: user.real_name,
                    username: user.username,
                    avatar: user.avatar,
                    department: user.department,
                    email: user.email,
                });
            }
        })
        .catch(() => {})
        .finally(() => {
            applySidebarPermissions();
            bootLlmAssistant();
            initRouter();
        });
});
