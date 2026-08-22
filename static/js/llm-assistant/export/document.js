/**
 * 将 AI 回答组装为可打印 / 可导出 Word 的独立 HTML 文档（仅正文，不含快照与操作）
 */

import { renderMarkdown } from '../markdown/render.js';
import { analysesKeyLabelZh } from '../report/labels.js';

/**
 * @param {object} msg
 * @returns {boolean}
 */
export function canExportAssistantMessage(msg) {
    if (msg?.role !== 'assistant') return false;
    if (msg.status === 'pending' || msg.status === 'error') return false;
    const content = String(msg.content || '').trim();
    if (!content || content === 'AI思考中…' || content.startsWith('AI思考中')) return false;
    return true;
}

/**
 * @param {object} msg
 * @returns {string}
 */
export function buildExportFilename(msg) {
    const id = msg?.report_id ? String(msg.report_id) : String(Date.now());
    const date = new Date().toISOString().slice(0, 10);
    return `AI分析报告_${id}_${date}.doc`;
}

/**
 * @param {object} msg
 * @param {{ forPreview?: boolean }} [options]
 * @returns {string}
 */
export function buildAssistantDocumentHtml(msg, options = {}) {
    const forPreview = Boolean(options.forPreview);
    const question = String(msg.user_question || '').trim();
    const scopeText = formatScope(msg.scope);
    const reportType = msg.resolved_report_type
        ? analysesKeyLabelZh(msg.resolved_report_type)
        : '';
    const generatedAt = formatDateTime(msg.generated_at);
    const reportId = msg.report_id ? `#${msg.report_id}` : '';
    const bodyHtml = renderMarkdown(msg.content || '');
    const footerParts = [];
    if (reportId) footerParts.push(`报告编号 ${reportId}`);
    if (msg.prompt_version) footerParts.push(msg.prompt_version);
    if (msg.from_cache) footerParts.push('缓存命中');
    const footerText = footerParts.join(' · ');

    const previewToolbar = forPreview
        ? `<div class="no-print preview-toolbar">
  <span class="preview-toolbar-title">AI 回答 · 打印预览</span>
  <div class="preview-toolbar-actions">
    <button type="button" class="preview-btn preview-btn-primary" onclick="window.print()">打印</button>
    <button type="button" class="preview-btn" onclick="window.close()">关闭</button>
  </div>
</div>`
        : '';

    const wordMeta = forPreview
        ? ''
        : `<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View><w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->`;

    return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40"
      lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="ProgId" content="Word.Document">
<meta name="Generator" content="STAMPING AI Assistant">
<title>AI 分析报告${reportId ? ` ${reportId}` : ''}</title>
${wordMeta}
<style>
${documentStyles()}
</style>
</head>
<body>
${previewToolbar}
<article class="doc">
  <header class="doc-header">
    <h1 class="doc-title">AI 分析报告</h1>
    <p class="doc-subtitle">汽车冲压件自动核价平台 · AI 助手</p>
  </header>
  <table class="meta-table" role="presentation">
    ${metaRow('提问', question || '—')}
    ${metaRow('分析范围', scopeText || '—')}
    ${metaRow('报告类型', reportType || '—')}
    ${metaRow('生成时间', generatedAt || '—')}
    ${reportId ? metaRow('报告编号', reportId) : ''}
  </table>
  <section class="llm-body" aria-label="AI 回答正文">
    ${bodyHtml}
  </section>
  ${footerText ? `<footer class="doc-footer">${escapeHtml(footerText)}</footer>` : ''}
</article>
</body>
</html>`;
}

/**
 * @param {string} label
 * @param {string} value
 * @returns {string}
 */
function metaRow(label, value) {
    return `<tr>
  <th>${escapeHtml(label)}</th>
  <td>${escapeHtml(value)}</td>
</tr>`;
}

/**
 * @param {object|null|undefined} scope
 * @returns {string}
 */
function formatScope(scope) {
    if (!scope || typeof scope !== 'object') return '';
    const parts = [];
    if (scope.location) parts.push(String(scope.location));
    if (scope.year) parts.push(`${scope.year}年`);
    if (scope.month) parts.push(`${scope.month}月`);
    if (scope.vehicle_model) parts.push(String(scope.vehicle_model));
    if (scope.bom_version) parts.push(`BOM ${scope.bom_version}`);
    if (scope.part_number) parts.push(String(scope.part_number));
    return parts.join(' · ');
}

/**
 * @param {string|null|undefined} iso
 * @returns {string}
 */
function formatDateTime(iso) {
    if (!iso) return '';
    try {
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) return String(iso);
        return date.toLocaleString('zh-CN', { hour12: false });
    } catch {
        return String(iso);
    }
}

/**
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * @returns {string}
 */
function documentStyles() {
    return `
@page { size: A4; margin: 2cm 2.2cm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 24px;
  font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
  font-size: 11pt;
  line-height: 1.75;
  color: #1a1a1a;
  background: #ffffff;
}
.doc { max-width: 720px; margin: 0 auto; }
.doc-header {
  border-bottom: 2px solid #d32f2f;
  padding-bottom: 12px;
  margin-bottom: 20px;
}
.doc-title {
  margin: 0;
  font-size: 20pt;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: 0.02em;
}
.doc-subtitle {
  margin: 6px 0 0;
  font-size: 10pt;
  color: #888888;
}
.meta-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 20px;
  font-size: 10pt;
}
.meta-table th {
  width: 88px;
  padding: 5px 12px 5px 0;
  text-align: left;
  font-weight: 600;
  color: #666666;
  vertical-align: top;
  white-space: nowrap;
}
.meta-table td {
  padding: 5px 0;
  color: #333333;
  word-break: break-word;
}
.llm-body h1 { font-size: 14pt; margin: 18px 0 8px; font-weight: 700; }
.llm-body h2 { font-size: 12pt; margin: 14px 0 6px; font-weight: 700; }
.llm-body h3 { font-size: 11pt; margin: 12px 0 4px; font-weight: 600; }
.llm-body p { margin: 6px 0; }
.llm-body ul, .llm-body ol { margin: 6px 0 6px 1.6em; padding: 0; }
.llm-body li { margin: 2px 0; }
.llm-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 10pt;
}
.llm-body th, .llm-body td {
  border: 1px solid #cccccc;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
.llm-body th { background: #f5f5f5; font-weight: 600; }
.llm-body code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9.5pt;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 2px;
}
.llm-body blockquote {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid #d32f2f;
  color: #555555;
  background: #fafafa;
}
.llm-body hr {
  border: none;
  border-top: 1px solid #dddddd;
  margin: 16px 0;
}
.doc-footer {
  margin-top: 28px;
  padding-top: 10px;
  border-top: 1px solid #dddddd;
  font-size: 9pt;
  color: #999999;
}
.no-print.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 720px;
  margin: 0 auto 20px;
  padding: 10px 14px;
  background: #f8f8f8;
  border: 1px solid #dddddd;
  border-radius: 4px;
}
.preview-toolbar-title {
  font-size: 10pt;
  font-weight: 600;
  color: #333333;
}
.preview-toolbar-actions { display: flex; gap: 8px; }
.preview-btn {
  padding: 6px 14px;
  font-size: 10pt;
  border: 1px solid #cccccc;
  border-radius: 3px;
  background: #ffffff;
  color: #333333;
  cursor: pointer;
}
.preview-btn-primary {
  background: #d32f2f;
  border-color: #d32f2f;
  color: #ffffff;
}
.preview-btn:hover { opacity: 0.9; }
@media print {
  body { padding: 0; }
  .no-print { display: none !important; }
}
`.trim();
}
