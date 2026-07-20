/**
 * Simple Router Module
 * 简单的 SPA 路由管理
 */
export class Router {
    constructor() {
        this.routes = new Map();
        this.currentPage = 'dashboard';
    }

    /**
     * 注册路由
     */
    register(pageName, page) {
        this.routes.set(pageName, page);
    }

    /**
     * 导航到指定页面
     */
    navigate(pageName) {
        if (!this.routes.has(pageName)) {
            console.warn(`Route ${pageName} not found`);
            return;
        }

        this.currentPage = pageName;
        const page = this.routes.get(pageName);

        // 更新页面标题
        this.updateTitle(pageName);

        // 更新导航高亮
        this.updateNavHighlight(pageName);

        // 渲染页面
        this.render(pageName, page);
    }

    /**
     * 更新页面标题
     */
    updateTitle(pageName) {
        const titleEl = document.getElementById('pageTitle');
        const breadcrumbEl = document.getElementById('breadcrumbItem');

        const titles = {
            dashboard: '仪表盘',
            'stamping-upload': '上传工艺文件',
            'stamping-parts': '零件列表',
            costing: '核价',
            quotation: '报价',
            settings: '系统设置',
        };

        if (titleEl) titleEl.textContent = titles[pageName] || pageName;
        if (breadcrumbEl) breadcrumbEl.textContent = titles[pageName] || pageName;
    }

    /**
     * 更新导航高亮
     */
    updateNavHighlight(pageName) {
        document.querySelectorAll('.sidebar-nav-link, .submenu-link').forEach(link => {
            link.classList.remove('active');
            if (link.dataset.page === pageName) {
                link.classList.add('active');
                const parent = link.closest('.submenu');
                if (parent) parent.classList.add('show');
            }
        });
    }

    /**
     * 渲染页面
     */
    render(pageName, page) {
        const content = document.getElementById('pageContent');
        const topActions = document.getElementById('topActions');

        if (!content) return;

        try {
            // 渲染 HTML
            content.innerHTML = page.render();

            // 初始化页面逻辑
            if (typeof page.init === 'function') {
                page.init();
            }
        } catch (error) {
            console.error('渲染页面失败:', error);
            content.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-600">加载失败: ${esc(error.message)}</div>`;
        }
    }

    /**
     * 获取当前页面
     */
    getCurrentPage() {
        return this.currentPage;
    }
}

// 全局路由实例
export const router = new Router();
