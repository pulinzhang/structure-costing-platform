/**
 * 将 AI 回答组装为可打印 / 可导出 Word 的独立 HTML 文档（仅正文，不含快照与操作）
 */

import { renderMarkdown } from '../markdown/render.js?v=6';
import { analysesKeyLabelZh } from '../report/labels.js';

/**
 * @param {object} msg
 * @returns {boolean}
 */
export function canExportAssistantMessage(msg) {
    if (msg?.role !== 'assistant') return false;
    if (msg.status === 'pending' || msg.status === 'error') return false;
    const content = String(msg.content || '').trim();
    if (
        !content
        || content.startsWith('AI思考中')
        || content.startsWith('AI正在思考中')
    ) {
        return false;
    }
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
 * @returns {string}
 */
export function buildAssistantDocumentHtml(msg) {
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

    const wordMeta = `<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View><w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->`;

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
<article class="doc">
  <header class="doc-header">
    <h1 class="doc-title">AI 分析报告</h1>
    <p class="doc-subtitle">结构件自动核价平台 · AI 助手整理，便于参阅，请以系统核算为准</p>
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
    if (scope.year || scope.month) parts.push(fmtPeriod(scope.year, scope.month));
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
.doc { max-width: 900px; margin: 0 auto; }
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
.llm-body .table-scroll {
  overflow-x: auto;
  max-width: 100%;
  margin: 10px 0;
}
.llm-body table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 9.5pt;
  line-height: 1.35;
}
.llm-body th, .llm-body td {
  border: 1px solid #cccccc;
  padding: 5px 8px;
  text-align: left;
  vertical-align: top;
}
.llm-body th {
  background: #f5f5f5;
  font-weight: 600;
  white-space: nowrap;
  word-break: keep-all;
}
.llm-body .cell-keep {
  white-space: nowrap;
  word-break: keep-all;
}
.llm-body .cell-wrap {
  max-width: 10.5em;
  word-break: break-word;
  overflow-wrap: break-word;
}
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
@media print {
  body { padding: 0; }
  .doc { max-width: none; }
  .llm-body .table-scroll { overflow: visible; }
  .llm-body table { font-size: 8.5pt; }
}
`.trim();
}
