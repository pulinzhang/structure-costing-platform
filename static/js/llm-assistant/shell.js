/**
 * 对话壳层状态机：closed | panel | maximized | docked
 * 请求仅传自然语言；回复仅展示 Markdown 正文。
 */

import { createReport, getReport } from './api.js';
import { mountComposer, setComposerBusy, setComposerCarry } from './chat/composer.js?v=9';
import { humanizeUserFacingError } from './errors.js';
import { renderThread } from './chat/thread.js?v=23';
import { printAssistantMessage, closePrintPreview } from './export/print.js?v=15';
import { downloadWordDocument } from './export/word.js?v=10';
import { findPrompt, fillPromptTemplate } from './prompts/catalog.js?v=9';
import { applyReportToMessage } from './report/apply-report.js?v=4';
import { openHistoryPanel } from './report/history.js?v=12';
import {
    buildStorageKey,
    clearConversation,
    loadConversation,
    saveConversation,
} from './storage/conversation.js';
import { applyPanelWidth, bindPanelResize } from './panel-size.js?v=2';
import { pollTask } from './task/poller.js';
import { panelClass, shellHtml } from './template.js?v=19';

/** @typedef {'closed'|'panel'|'maximized'|'docked'} AssistantMode */

export function createShell(options) {
    const canView = Boolean(options.canView);
    const canRun = Boolean(options.canRun);
    const getUserId = options.getUserId || (() => 'anon');

    /** @type {AssistantMode} */
    let mode = 'closed';
    let messages = [];
    let conversationId = `c_local_${Date.now()}`;
    let busy = false;
    /** 用户拿掉沿用条之后，下一问不再带上一份报告，直到这次提问自己写出新报告。 */
    let carrySuppressed = false;
    /** @type {AbortController|null} */
    let pollAbort = null;

    let root = document.getElementById('llmAssistantRoot');
    if (!root) {
        root = document.createElement('div');
        root.id = 'llmAssistantRoot';
        document.body.appendChild(root);
    }
    root.innerHTML = shellHtml();

    const els = {
        mask: root.querySelector('#llmAssistantMask'),
        dock: document.getElementById('llmAssistantDock'),
        panel: root.querySelector('#llmAssistantPanel'),
        status: root.querySelector('#llmAssistantStatus'),
        thread: root.querySelector('#llmThread'),
        history: root.querySelector('#llmHistoryOverlay'),
        composer: root.querySelector('#llmComposer'),
    };

    remountComposer();
    reloadThread();
    bindPanelResize(els.panel, { isMaximized: () => mode === 'maximized' });
    applyMode('closed');

    els.dock?.addEventListener('click', () => {
        const open = mode === 'panel' || mode === 'maximized';
        setMode(open ? 'docked' : 'panel');
    });
    els.mask?.addEventListener('click', () => setMode('docked'));
    root.querySelector('#llmBtnDock')?.addEventListener('click', () => setMode('docked'));
    root.querySelector('#llmBtnMaximize')?.addEventListener('click', () => {
        setMode(mode === 'maximized' ? 'panel' : 'maximized');
    });
    root.querySelector('#llmBtnHistory')?.addEventListener('click', () => {
        closePrintPreview();
        void openHistoryPanel(els.history, {
            onSelect: (reportId) => {
                els.history?.classList.add('hidden');
                void reopenReport(reportId);
            },
            onDeleted: (reportId) => {
                const before = messages.length;
                messages = messages.filter(
                    (msg) => Number(msg.report_id) !== Number(reportId),
                );
                if (messages.length !== before) {
                    renderThread(els.thread, messages);
                    persist();
                }
            },
            onClose: () => {},
        });
    });
    root.querySelector('#llmBtnClearChat')?.addEventListener('click', () => {
        clearConversation(storageKey());
        messages = [];
        conversationId = `c_local_${Date.now()}`;
        renderThread(els.thread, messages);
        setStatus('已清空本机对话');
        refreshComposerCarry();
    });

    els.thread?.addEventListener('click', (event) => {
        const copyBtn = event.target.closest('[data-llm-copy-question]');
        if (copyBtn) {
            const msgId = copyBtn.getAttribute('data-msg-id');
            const msg = messages.find((item) => item.id === msgId);
            const text = String(msg?.content || '').trim();
            if (text) void copyQuestionText(text);
            return;
        }
        const exportBtn = event.target.closest('[data-llm-export]');
        if (exportBtn) {
            const msgId = exportBtn.getAttribute('data-msg-id');
            const exportType = exportBtn.getAttribute('data-llm-export');
            const msg = messages.find((item) => item.id === msgId);
            if (!msg) return;
            if (exportType === 'print') {
                closePrintPreview();
                els.history?.classList.add('hidden');
                printAssistantMessage(msg);
            } else if (exportType === 'word') {
                downloadWordDocument(msg);
            }
            return;
        }
    });

    async function copyQuestionText(text) {
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                copyWithTextarea(text);
            }
            window.showToast?.('已复制', 'success');
        } catch (_error) {
            try {
                copyWithTextarea(text);
                window.showToast?.('已复制', 'success');
            } catch (_fallbackError) {
                window.showToast?.('复制失败', 'error');
            }
        }
    }

    function copyWithTextarea(text) {
        const area = document.createElement('textarea');
        area.value = text;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.left = '-9999px';
        document.body.appendChild(area);
        area.select();
        const copied = document.execCommand('copy');
        area.remove();
        if (!copied) throw new Error('copy failed');
    }

    function storageKey() {
        return buildStorageKey(getUserId());
    }

    function reloadThread() {
        const stored = loadConversation(storageKey());
        conversationId = stored.conversation_id;
        messages = stored.messages || [];
        renderThread(els.thread, messages);
        refreshComposerCarry();
    }

    function remountComposer() {
        mountComposer(els.composer, {
            canRun,
            busy,
            onSubmit: (text) => {
                void submitQuestion({
                    text,
                    audience: null,
                    prompt_id: null,
                });
            },
            onDismissCarry: () => dismissCarry(),
        });
        refreshComposerCarry();
    }

    function setBusy(next) {
        busy = next;
        setComposerBusy(els.composer, busy, canRun);
    }

    function setStatus(text) {
        if (!els.status) return;
        const label = String(text || '');
        const quiet = isQuietStatus(label);
        els.status.textContent = quiet ? '' : label;
        els.status.classList.toggle('hidden', quiet);
    }

    /**
     * 空闲和做完的提示不占标题。进行中和失败才显示。
     * @param {string} label
     * @returns {boolean}
     */
    function isQuietStatus(label) {
        if (!label || label === '就绪') return true;
        if (label === '完成' || label === '完成（缓存）' || label === '已完成' || label === '命中缓存') return true;
        if (label === '已清空本机对话') return true;
        if (label.startsWith('已在对话中') || label.startsWith('已打开')) return true;
        return false;
    }

    function persist() {
        saveConversation(storageKey(), {
            conversation_id: conversationId,
            messages,
        });
        refreshComposerCarry();
    }

    function dismissCarry() {
        carrySuppressed = true;
        refreshComposerCarry();
    }

    function findPreviousReportId() {
        if (carrySuppressed) return null;
        // 只沿用本线程提交或空线程种子。历史只读插入 (source=history) 和帮助回答不送 id。
        for (let index = messages.length - 1; index >= 0; index -= 1) {
            const msg = messages[index];
            if (msg?.role !== 'assistant') continue;
            const source = msg.source || 'submit';
            if (source !== 'submit' && source !== 'seed') continue;
            if (String(msg.resolved_report_type || '') === 'usage_help') continue;
            const reportId = Number(msg.report_id);
            if (reportId) return reportId;
        }
        return null;
    }

    function refreshComposerCarry() {
        if (carrySuppressed) {
            setComposerCarry(els.composer, null, null);
            return;
        }
        const previousId = findPreviousReportId();
        const sourceMsg = previousId
            ? [...messages].reverse().find((item) => Number(item.report_id) === Number(previousId))
            : null;
        setComposerCarry(els.composer, sourceMsg?.carry || null, sourceMsg?.scope || null);
    }

    /**
     * 顶栏入口一直留着。打开时字色变实，收起时回到和帮助一样的灰。
     * @param {boolean} showPanel
     */
    function syncDock(showPanel) {
        if (!els.dock) return;
        els.dock.classList.remove('hidden');
        els.dock.classList.add('inline-flex');
        els.dock.setAttribute('aria-expanded', showPanel ? 'true' : 'false');
        els.dock.classList.toggle('text-ink', showPanel);
        els.dock.classList.toggle('text-ink-muted', !showPanel);
    }

    function applyMode(next) {
        mode = next;
        const showPanel = mode === 'panel' || mode === 'maximized';
        const opening = showPanel && Boolean(els.panel?.classList.contains('hidden'));

        els.panel?.classList.toggle('hidden', !showPanel);
        syncDock(showPanel);
        els.mask?.classList.toggle('hidden', !showPanel);
        if (opening) focusComposer();
        els.history?.classList.add('hidden');
        closePrintPreview();

        if (els.panel) {
            els.panel.className = panelClass(mode === 'maximized');
            if (!showPanel) els.panel.classList.add('hidden');
            applyPanelWidth(els.panel, mode === 'maximized');
        }
    }

    function focusComposer() {
        const input = els.composer?.querySelector('#llmComposerInput');
        if (input instanceof HTMLTextAreaElement && !input.disabled) {
            input.focus();
        }
    }

    function setMode(next) {
        applyMode(next);
    }

    /**
     * @param {number} reportId
     */
    async function reopenReport(reportId) {
        if (busy) return;
        const existingIndex = messages.findIndex(
            (item) => Number(item.report_id) === Number(reportId),
        );
        if (existingIndex >= 0) {
            setStatus(`已在对话中 #${reportId}`);
            renderThread(els.thread, messages);
            return;
        }
        setBusy(true);
        setStatus('加载历史分析…');
        // 空线程打开历史 = 种子（下一问可沿用）；非空线程打开 = 只读，不劫持当前沿用。
        const isSeed = messages.length === 0;
        try {
            const report = await getReport(reportId);
            const question = String(report?.user_question || '').trim() || '（无问句）';
            const userMsg = {
                id: `m_${Date.now()}_u`,
                role: 'user',
                content: question,
                created_at: report?.metadata?.generated_at || new Date().toISOString(),
            };
            const assistantMsg = {
                id: `m_${Date.now()}_a`,
                role: 'assistant',
                content: '',
                status: 'done',
                created_at: new Date().toISOString(),
            };
            applyReportToMessage(assistantMsg, report);
            assistantMsg.source = isSeed ? 'seed' : 'history';
            messages = [...messages, userMsg, assistantMsg];
            renderThread(els.thread, messages);
            persist();
            setStatus(`已打开 #${reportId}`);
        } catch (error) {
            window.showToast?.(error?.message || '加载失败', 'error');
            setStatus('加载失败');
        } finally {
            setBusy(false);
        }
    }

    /**
     * @param {{
     *   promptId?: string,
     *   part_number?: string,
     *   autoSend?: boolean,
     * }=} opts
     */
    function open(opts = {}) {
        if (!canView) {
            window.showToast?.('无采购分析查看权限', 'warning');
            return;
        }
        reloadThread();
        setMode('panel');

        const promptId = opts.promptId || null;
        if (promptId) {
            const item = findPrompt(promptId);
            if (item) {
                const text = fillPromptTemplate(item.label, {
                    part_number: opts.part_number || '',
                });
                if (opts.autoSend !== false) {
                    void submitQuestion({
                        text,
                        audience: item.audience,
                        prompt_id: item.id,
                        needs_part_number: item.needs_part_number && !opts.part_number,
                    });
                }
            }
        }
    }

    function close() {
        if (pollAbort) {
            pollAbort.abort();
            pollAbort = null;
        }
        setBusy(false);
        setStatus('就绪');
        applyMode('closed');
    }

    /**
     * @param {{
     *   text: string,
     *   audience?: string|null,
     *   prompt_id?: string|null,
     *   needs_part_number?: boolean,
     * }} payload
     */
    async function submitQuestion(payload) {
        if (!canRun) {
            window.showToast?.('无采购分析生成权限', 'warning');
            return;
        }
        if (busy) return;

        let question = String(payload.text || '').trim();
        if (!question) return;

        if (payload.needs_part_number && question.includes('{part_number}')) {
            const part = window.prompt('请输入零件号');
            if (!part || !String(part).trim()) {
                window.showToast?.('零件号不能为空', 'warning');
                return;
            }
            question = fillPromptTemplate(
                findPrompt(payload.prompt_id)?.label || question,
                { part_number: String(part).trim() },
            );
        }

        const clearsSuppression = carrySuppressed;
        const previousReportId = findPreviousReportId();
        const userMsg = {
            id: `m_${Date.now()}_u`,
            role: 'user',
            content: question,
            created_at: new Date().toISOString(),
        };
        const assistantMsg = {
            id: `m_${Date.now()}_a`,
            role: 'assistant',
            source: 'submit',
            content: '思考中…',
            status: 'pending',
            created_at: new Date().toISOString(),
        };
        messages = [...messages, userMsg, assistantMsg];
        renderThread(els.thread, messages, { stick: true });
        persist();
        setBusy(true);
        setStatus('已提交分析…');

        try {
            const body = {
                user_question: question,
                audience: payload.audience || null,
                force_refresh: false,
            };
            if (previousReportId) {
                body.previous_report_id = previousReportId;
            }

            const task = await createReport(body);
            const reportId = task.report_id;
            const taskId = task.task_id;
            assistantMsg.report_id = reportId;
            assistantMsg.task_id = taskId;
            assistantMsg.source = 'submit';
            if (task.carry) assistantMsg.carry = task.carry;
            if (task.scope) assistantMsg.scope = task.scope;
            if (task.resolved_report_type) assistantMsg.resolved_report_type = task.resolved_report_type;
            if (clearsSuppression) carrySuppressed = false;
            persist();

            let report = null;
            const canSkipPoll = task.status === 'succeeded';
            if (canSkipPoll) {
                setStatus(task.from_cache ? '命中缓存' : '已完成');
                report = await getReport(reportId);
            } else if (task.status === 'failed') {
                report = await getReport(reportId);
                throw new Error(report?.error_message || task.message || '分析失败');
            } else {
                if (pollAbort) pollAbort.abort();
                pollAbort = new AbortController();
                setStatus(task.message || 'AI正在思考中…');
                await pollTask(taskId, {
                    signal: pollAbort.signal,
                    onProgress: (data) => {
                        const pct = data?.progress ?? 0;
                        const msg = data?.msg || 'AI正在思考中…';
                        setStatus(`${msg} ${pct}%`);
                        assistantMsg.content = `${msg}（${pct}%）`;
                        renderThread(els.thread, messages);
                    },
                });
                report = await getReport(reportId);
            }

            if (report?.status === 'failed') {
                throw new Error(report.error_message || '分析失败');
            }

            applyReportToMessage(assistantMsg, report);
            setStatus(assistantMsg.from_cache ? '完成（缓存）' : '完成');
            renderThread(els.thread, messages);
            persist();
        } catch (error) {
            assistantMsg.status = 'error';
            assistantMsg.content = humanizeUserFacingError(error?.message || error);
            setStatus('失败');
            renderThread(els.thread, messages);
            persist();
            if (!error?.status) {
                window.showToast?.(assistantMsg.content, 'error');
            }
        } finally {
            setBusy(false);
            pollAbort = null;
        }
    }

    return {
        open,
        close,
        setMode,
        getMode: () => mode,
        reopenReport,
    };
}

