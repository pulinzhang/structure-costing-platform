/**
 * 消息线程
 */

import { renderMarkdown } from '../markdown/render.js';

/**
 * @param {HTMLElement} root
 * @param {object[]} messages
 */
export function renderThread(root, messages) {
    if (!root) return;
    if (!Array.isArray(messages) || messages.length === 0) {
        root.innerHTML = `
<div class="flex flex-col items-center justify-center h-full min-h-[160px] text-center px-4">
  <p class="text-xs text-[#757575]">先补齐上方范围，再点常见问题或直接提问</p>
  <p class="text-[10px] text-[#484848] mt-1">对话仅保存在本机浏览器</p>
</div>`;
        return;
    }

    root.innerHTML = messages.map((msg) => renderMessage(msg)).join('');
    root.scrollTop = root.scrollHeight;
}

/**
 * @param {object} msg
 * @returns {string}
 */
function renderMessage(msg) {
    const isUser = msg.role === 'user';
    const bubbleClass = isUser
        ? 'ml-8 bg-[#1e1e1e] border border-[#2c2c2c] text-[#F5F5F5]'
        : 'mr-6 bg-[#141414] border border-[#222222] text-[#E8E8E8]';

    let body;
    if (msg.status === 'pending') {
        body = `<div class="text-[11px] text-[#9e9e9e] flex items-center gap-2">
          <span class="inline-block w-3 h-3 border border-[#616161] border-t-[#ff5252] rounded-full animate-spin"></span>
          <span>${esc(msg.content || '分析中…')}</span>
        </div>`;
    } else if (msg.status === 'error') {
        body = `<div class="text-[11px] text-[#ef5350]">${esc(msg.content || '分析失败')}</div>`;
    } else if (!isUser) {
        body = `<div class="llm-md text-[11px] leading-relaxed [&_h1]:text-sm [&_h2]:text-xs [&_h3]:text-[11px] [&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-4 [&_code]:font-mono [&_code]:text-[10px] [&_code]:text-[#ff8a80]">${renderMarkdown(msg.content || '')}</div>`;
    } else {
        body = `<div class="text-[11px] whitespace-pre-wrap break-words">${esc(msg.content || '')}</div>`;
    }

    const meta = msg.prompt_version
        ? `<div class="mt-1.5 text-[9px] font-mono text-[#3a3a3a]">${esc(msg.prompt_version)}</div>`
        : '';

    return `
<div class="flex ${isUser ? 'justify-end' : 'justify-start'}" data-msg-id="${escAttr(msg.id)}">
  <div class="max-w-[92%] px-2.5 py-2 rounded-sm ${bubbleClass}">
    ${body}
    ${meta}
  </div>
</div>`;
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escAttr(value) {
    return esc(value).replace(/'/g, '&#39;');
}
