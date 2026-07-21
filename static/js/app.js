/**
 * 汽车冲压件自动核价平台 - SPA 主应用
 *
 * 架构说明：
 * - 采用关注点分离（SoC）原则
 * - modules/*.js    : HTML 模板函数
 * - pages/*.js      : 页面逻辑模块（init 初始化）
 * - app.js          : SPA 核心（路由、渲染、页面注册）
 */

import { pageMeta } from './modules/index.js';
import { dashboardTemplate } from './modules/dashboard.js';
import { uploadTemplate } from './modules/upload.js';
import { partsTemplate } from './modules/parts.js';
import { costingTemplate } from './modules/costing.js';
import { quotationTemplate } from './modules/quotation.js';
import { settingsTemplate } from './modules/settings.js';

import { DashboardPage } from './pages/dashboard.js';
import { UploadPage } from './pages/upload.js';
import { PartsPage } from './pages/parts.js';

// ===== 页面注册 =====
// 每个页面模块必须实现 init() 方法

const pages = {
    dashboard: {
        render: dashboardTemplate,
        init: () => DashboardPage.init(),
    },
    'stamping-upload': {
        render: uploadTemplate,
        init: () => UploadPage.init(),
    },
    'stamping-parts': {
        render: partsTemplate,
        init: () => PartsPage.init(),
    },
    costing: {
        render: costingTemplate,
        init: () => {},
    },
    quotation: {
        render: quotationTemplate,
        init: () => {},
    },
    settings: {
        render: settingsTemplate,
        init: () => {},
    },
};

// ===== 路由控制 =====

function renderPage(pageName) {
    const page = pages[pageName];
    if (!page) {
        document.getElementById('pageContent').innerHTML =
            '<div class="text-center text-slate-500 py-12">页面不存在</div>';
        return;
    }

    const content = document.getElementById('pageContent');
    const title = document.getElementById('pageTitle');
    const breadcrumb = document.getElementById('breadcrumbItem');
    const topActions = document.getElementById('topActions');

    // 更新导航高亮
    document.querySelectorAll('.sidebar-nav-link, .submenu-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === pageName) {
            link.classList.add('active');
            const parent = link.closest('.submenu');
            if (parent) parent.classList.add('show');
        }
    });

    // 更新标题
    const meta = pageMeta[pageName] || { title: pageName, breadcrumb: pageName };
    if (title) title.textContent = meta.title;
    if (breadcrumb) breadcrumb.textContent = meta.breadcrumb;
    if (topActions) topActions.innerHTML = '';

    try {
        content.innerHTML = page.render();
        page.init();
    } catch (error) {
        console.error('渲染页面失败:', error);
        content.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-600">加载失败: ${esc(error.message)}</div>`;
    }
}

// ===== 全局事件委托 =====

document.addEventListener('click', function(e) {
    // 页面导航链接（事件委托，支持动态渲染的内容）
    const link = e.target.closest('[data-page]');
    if (link) {
        e.preventDefault();
        const pageName = link.getAttribute('data-page');
        renderPage(pageName);
        return;
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // 初始化侧边栏子菜单
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
                    if (otherSubmenu) otherSubmenu.classList.remove('show');
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

    // 初始化仪表盘
    renderPage('dashboard');
});
