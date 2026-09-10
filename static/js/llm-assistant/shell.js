/**

 * 对话壳层状态机：closed | panel | maximized | docked

 * 请求仅传自然语言；回复仅展示 Markdown 正文。

 */



import { createReport, getReport } from './api.js';

import { mountChips, setChipsDisabled, setChipsVisible } from './chat/chips.js';

import { mountComposer, setComposerBusy } from './chat/composer.js';

import { humanizeUserFacingError } from './errors.js';
import { renderThread } from './chat/thread.js?v=9';

import { printAssistantMessage, closePrintPreview } from './export/print.js?v=9';

import { downloadWordDocument } from './export/word.js?v=5';

import { findPrompt, fillPromptTemplate } from './prompts/catalog.js?v=4';

import { applyReportToMessage } from './report/apply-report.js';

import { openHistoryPanel } from './report/history.js?v=7';

import {

    buildStorageKey,

    clearConversation,

    loadConversation,

    saveConversation,

} from './storage/conversation.js';

import { pollTask } from './task/poller.js';

import { entryButtonHtml, shellHtml } from './template.js?v=5';



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

    /** @type {AbortController|null} */

    let pollAbort = null;



    const entryHost = options.entryHost;

    if (entryHost && canView) {

        entryHost.innerHTML = entryButtonHtml();

    }



    let root = document.getElementById('llmAssistantRoot');

    if (!root) {

        root = document.createElement('div');

        root.id = 'llmAssistantRoot';

        document.body.appendChild(root);

    }

    root.innerHTML = shellHtml();



    const els = {

        mask: root.querySelector('#llmAssistantMask'),

        dock: root.querySelector('#llmAssistantDock'),

        panel: root.querySelector('#llmAssistantPanel'),

        status: root.querySelector('#llmAssistantStatus'),

        thread: root.querySelector('#llmThread'),

        history: root.querySelector('#llmHistoryOverlay'),

        chips: root.querySelector('#llmChips'),

        composer: root.querySelector('#llmComposer'),

        entryBtn: entryHost?.querySelector('#llmAssistantEntryBtn'),

    };



    remountChips();

    remountComposer();

    reloadThread();

    applyMode('closed');



    els.entryBtn?.addEventListener('click', () => open());

    els.dock?.addEventListener('click', () => setMode('panel'));

    els.mask?.addEventListener('click', () => setMode('docked'));

    root.querySelector('#llmBtnClose')?.addEventListener('click', () => close());

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

                    updateChipsVisibility();

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

        updateChipsVisibility();

    });



    els.thread?.addEventListener('click', (event) => {

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



    function storageKey() {

        return buildStorageKey(getUserId());

    }



    function reloadThread() {

        const stored = loadConversation(storageKey());

        conversationId = stored.conversation_id;

        messages = stored.messages || [];

        renderThread(els.thread, messages);

        updateChipsVisibility();

    }



    function updateChipsVisibility() {

        setChipsVisible(els.chips, messages.length === 0);

    }



    function remountChips() {

        mountChips(els.chips, {

            disabled: busy || !canRun,

            onPick: (item, text) => {

                void submitQuestion({

                    text,

                    audience: item.audience,

                    prompt_id: item.id,

                    needs_part_number: item.needs_part_number,

                });

            },

        });

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

        });

    }



    function setBusy(next) {

        busy = next;

        setComposerBusy(els.composer, busy, canRun);

        setChipsDisabled(els.chips, busy || !canRun);

    }



    function setStatus(text) {

        if (els.status) els.status.textContent = text || '就绪';

    }



    function persist() {

        saveConversation(storageKey(), {

            conversation_id: conversationId,

            messages,

        });

    }



    function applyMode(next) {

        mode = next;

        const showPanel = mode === 'panel' || mode === 'maximized';

        const showDock = mode === 'docked';

        const showMask = showPanel;



        els.panel?.classList.toggle('hidden', !showPanel);

        els.dock?.classList.toggle('hidden', !showDock);

        els.dock?.classList.toggle('flex', showDock);

        els.mask?.classList.toggle('hidden', !showMask);

        els.history?.classList.add('hidden');

        closePrintPreview();



        if (els.panel) {

            if (mode === 'maximized') {

                els.panel.className =

                    'fixed z-[110] flex flex-col overflow-hidden border border-[#2c2c2c] bg-[#121212] ' +

                    'left-4 right-4 top-4 bottom-4 w-auto h-auto shadow-[0_16px_48px_rgba(0,0,0,0.65)]';

            } else {

                els.panel.className =

                    'fixed z-[110] flex flex-col overflow-hidden border border-[#2c2c2c] bg-[#121212] ' +

                    'w-[min(420px,calc(100vw-1.5rem))] top-4 bottom-4 right-4 h-auto ' +

                    'shadow-[0_16px_48px_rgba(0,0,0,0.65)]';

            }

            if (!showPanel) els.panel.classList.add('hidden');

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

            messages = [...messages, userMsg, assistantMsg];

            renderThread(els.thread, messages);

            persist();

            updateChipsVisibility();

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

        remountChips();

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



        const userMsg = {

            id: `m_${Date.now()}_u`,

            role: 'user',

            content: question,

            created_at: new Date().toISOString(),

        };

        const assistantMsg = {

            id: `m_${Date.now()}_a`,

            role: 'assistant',

            content: '思考中…',

            status: 'pending',

            created_at: new Date().toISOString(),

        };

        messages = [...messages, userMsg, assistantMsg];

        renderThread(els.thread, messages);

        updateChipsVisibility();

        persist();

        setBusy(true);

        setStatus('已提交分析…');



        try {

            const body = {

                user_question: question,

                audience: payload.audience || null,

                force_refresh: false,

            };



            const task = await createReport(body);

            const reportId = task.report_id;

            const taskId = task.task_id;

            assistantMsg.report_id = reportId;

            assistantMsg.task_id = taskId;



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

            remountChips();

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


