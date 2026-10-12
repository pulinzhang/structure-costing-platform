/**
 * 上传页右侧「最近上传」。只记本次打开后导入成功的文件，刷新即清空。
 */

const MAX_RECENT_UPLOADS = 8;
const EMPTY_MARKUP = '<p class="text-[10px] text-ink-faint text-center py-5">暂无上传记录</p>';
const SURFACE_SHELL = 'bg-app-surface border border-line';

export function recentUploadsCardHtml(containerId, shellClass = SURFACE_SHELL) {
    return `
                <div class="${shellClass}">
                    <div class="px-4 py-3 border-b border-line-subtle">
                        <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">最近上传</h5>
                    </div>
                    <div class="p-4" id="${containerId}">
                        ${EMPTY_MARKUP}
                    </div>
                </div>`;
}

function paint(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!items.length) {
        container.innerHTML = EMPTY_MARKUP;
        return;
    }
    container.innerHTML = items.map((item) => {
        const meta = [item.scopeLabel, item.timeLabel].filter(Boolean).join(' · ');
        return `
        <div class="flex items-start gap-2.5 p-2.5 bg-app-main border border-line mb-2 last:mb-0">
            <span class="text-ok shrink-0 mt-0.5">${window.svgIcon('file-earmark-excel')}</span>
            <div class="min-w-0 flex-1">
                <p class="text-[11px] text-ink truncate">${window.esc(item.fileName)}</p>
                <p class="text-[10px] text-ink-dim mt-0.5">${window.esc(meta)}</p>
                ${item.summary ? `<p class="text-[10px] text-ink-muted mt-0.5">${window.esc(item.summary)}</p>` : ''}
            </div>
        </div>`;
    }).join('');
}

export function bindRecentUploads(containerId) {
    let items = [];
    return {
        paint() {
            paint(containerId, items);
        },
        remember(entry) {
            if (!entry?.fileName) return;
            const timeLabel = new Date().toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
            items = [
                {
                    fileName: entry.fileName,
                    scopeLabel: entry.scopeLabel || '',
                    summary: entry.summary || '',
                    timeLabel,
                },
                ...items,
            ].slice(0, MAX_RECENT_UPLOADS);
            paint(containerId, items);
        },
    };
}
