/**
 * AI 分析报告独立页（画册浅色 · 与总成核价计算报告同系）
 */

import { getReport } from '../api.js';
import { applyReportToMessage } from '../report/apply-report.js';
import { analysesKeyLabelZh } from '../report/labels.js';
import { renderMarkdown } from '../markdown/render.js?v=7';
import {
    buildAssistantDocumentHtml,
    buildExportFilename,
    canExportAssistantMessage,
} from '../export/document.js?v=12';

const state = {
    reportId: 0,
    msg: null,
};

function showToast(message, type) {
    const node = document.getElementById('reportToast');
    if (!node) return;
    node.textContent = message;
    node.classList.toggle('is-error', type === 'error');
    node.classList.add('is-on');
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => node.classList.remove('is-on'), 2600);
}

function display(value) {
    if (value == null || value === '') return '—';
    return window.esc(value);
}

function reportIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return parseInt(params.get('report_id') || '', 10);
}

function formatWhen(iso) {
    if (!iso) return '—';
    try {
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) return String(iso);
        return date.toLocaleString('zh-CN', { hour12: false });
    } catch {
        return String(iso);
    }
}

function printDateText() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    return `${now.getFullYear()}年${month}月${day}日 ${hour}:${minute}`;
}

function periodText(scope) {
    if (!scope) return '';
    if (typeof window.fmtPeriod === 'function') {
        return window.fmtPeriod(scope.year, scope.month);
    }
    return [scope.year, scope.month].filter(Boolean).join('-');
}

function scopeLine(scope) {
    if (!scope) return '';
    return [scope.location, scope.vehicle_model, scope.bom_version]
        .filter(Boolean)
        .join(' / ');
}

function printHeadInnerHtml() {
    const msg = state.msg || {};
    const scope = msg.scope || {};
    const meta = [
        scopeLine(scope) || '—',
        periodText(scope),
        msg.report_id ? `#${msg.report_id}` : '',
        `打印 ${printDateText()}`,
    ].filter(Boolean);
    return `
        <div class="print-running-brand">
            <span class="print-kicker">AI Analysis Report</span>
            <strong>AI 分析报告</strong>
        </div>
        <div class="print-running-meta">
            ${meta.map((item) => `<span>${display(item)}</span>`).join('')}
        </div>
    `;
}

function paintPrintHead() {
    const node = document.getElementById('reportPrintHead');
    if (!node || !state.msg) return;
    node.innerHTML = printHeadInnerHtml();
}

function printBannerRowHtml() {
    return `
        <tr class="print-page-banner">
            <th>
                <div class="print-running-head" id="reportPrintHead">${printHeadInnerHtml()}</div>
            </th>
        </tr>
    `;
}

function showError(root, message) {
    root.innerHTML = `<p class="error">${display(message)}</p>`;
}

function render(root) {
    const msg = state.msg;
    const scope = msg.scope || {};
    const reportType = msg.resolved_report_type
        ? analysesKeyLabelZh(msg.resolved_report_type)
        : '';
    const question = String(msg.user_question || '').trim();
    const footerParts = [];
    if (msg.report_id) footerParts.push(`报告编号 #${msg.report_id}`);
    if (msg.prompt_version) footerParts.push(msg.prompt_version);
    if (msg.from_cache) footerParts.push('缓存命中');
    footerParts.push('AI 助手整理，便于参阅，请以系统核算为准');
    const titleBits = [periodText(scope), scope.vehicle_model].filter(Boolean);
    document.title = titleBits.length
        ? `AI 分析报告 · ${titleBits.join(' · ')}`
        : `AI 分析报告${msg.report_id ? ` #${msg.report_id}` : ''}`;

    root.innerHTML = `
        <header class="report-head">
            <div>
                <p>AI Analysis Report</p>
                <h1>AI 分析报告</h1>
            </div>
            <div class="report-actions">
                <span class="export-hint">含刊头、提问与分析正文。快捷键 Ctrl+E 导出 Word</span>
                <button type="button" id="reportPrintBtn">打印</button>
                <button type="button" id="reportExportBtn" class="btn-export">导出 Word</button>
            </div>
        </header>
        <div class="meta">
            <div>范围 <strong>${display(scopeLine(scope))}</strong></div>
            <div>核价期 <strong>${display(periodText(scope))}</strong></div>
            <div>报告类型 <strong>${display(reportType)}</strong></div>
            <div>报告编号 <strong>${display(msg.report_id ? `#${msg.report_id}` : '')}</strong></div>
            <div>生成时间 <strong>${display(formatWhen(msg.generated_at))}</strong></div>
            ${scope.part_number ? `<div>零件号 <strong>${display(scope.part_number)}</strong></div>` : ''}
        </div>
        <div class="body">
            <table class="print-frame">
                <thead>${printBannerRowHtml()}</thead>
                <tbody>
                    <tr>
                        <td>
                            ${question ? `<p class="summary">提问</p><div class="narrative">${display(question)}</div>` : ''}
                            <section class="llm-body" aria-label="AI 回答正文">
                                ${renderMarkdown(msg.content || '')}
                            </section>
                            <footer class="doc-footer">${display(footerParts.join(' · '))}</footer>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;

    root.querySelector('#reportPrintBtn')?.addEventListener('click', () => {
        window.print();
    });
    root.querySelector('#reportExportBtn')?.addEventListener('click', exportWord);
}

function exportWord() {
    const msg = state.msg;
    if (!canExportAssistantMessage(msg)) {
        showToast('暂无可导出的 AI 回答', 'error');
        return;
    }
    if (typeof window.refuseWeChatDownload === 'function' && window.refuseWeChatDownload()) return;
    const html = buildAssistantDocumentHtml(msg);
    const blob = new Blob(['\ufeff', html], { type: 'application/msword;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = buildExportFilename(msg);
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast('Word 文档已导出');
}

function onKeydown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'e') {
        event.preventDefault();
        exportWord();
    }
}

async function boot() {
    const root = document.getElementById('reportRoot');
    const reportId = reportIdFromUrl();
    if (!Number.isFinite(reportId) || reportId <= 0) {
        showError(root, '缺少 report_id。');
        return;
    }
    state.reportId = reportId;
    document.title = `AI 分析报告 #${reportId}`;
    document.addEventListener('keydown', onKeydown);
    window.addEventListener('beforeprint', paintPrintHead);

    try {
        const report = await getReport(reportId);
        if (report?.status === 'failed') {
            showError(root, report.error_message || '报告生成失败');
            return;
        }
        if (report?.status && report.status !== 'succeeded') {
            showError(root, '报告尚未生成完成，请稍后刷新。');
            return;
        }
        state.msg = applyReportToMessage({ role: 'assistant' }, report);
        render(root);
    } catch (error) {
        showError(root, error?.message || '加载失败');
    }
}

boot();
