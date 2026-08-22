/**
 * 对话壳层状态机：closed | panel | maximized | docked
 */

import { createReport, getReport } from './api.js';
import { mountChips, setChipsDisabled } from './chat/chips.js';
import { mountComposer, setComposerBusy } from './chat/composer.js';
import { renderThread } from './chat/thread.js';
import { findPrompt, fillPromptTemplate } from './prompts/catalog.js';
import {
    defaultScope,
    mountScopeBar,
    readScope,
    validateScope,
    writeScope,
} from './scope/bar.js';
import {
    buildStorageKey,
    clearConversation,
    loadConversation,
    loadLastScope,
    saveConversation,
    saveLastScope,
} from './storage/conversation.js';
import { pollTask } from './task/poller.js';
import { entryButtonHtml, shellHtml } from './template.js';

/** @typedef {'closed'|'panel'|'maximized'|'docked'} AssistantMode */

export function createShell(options) {
    const canView = Boolean(options.canView);
    const canRun = Boolean(options.canRun);
    const getUserId = options.getUserId || (() => 'anon');

    /** @type {AssistantMode} */
    let mode = 'closed';
    let scope = { ...defaultScope(), ...(loadLastScope() || {}) };
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
        scopeBar: root.querySelector('#llmScopeBar'),
        thread: root.querySelector('#llmThread'),
        chips: root.querySelector('#llmChips'),
        composer: root.querySelector('#llmComposer'),
        promptMeta: root.querySelector('#llmPromptMeta'),
        entryBtn: entryHost?.querySelector('#llmAssistantEntryBtn'),
    };

    mountScopeBar(els.scopeBar, {
        scope,
        onChange: (next) => {
            scope = next;
            saveLastScope(scope);
            reloadThreadForScope();
            remountChips();
        },
    });

    remountChips();
    remountComposer();
    reloadThreadForScope();
    applyMode('closed');

    els.entryBtn?.addEventListener('click', () => open());
    els.dock?.addEventListener('click', () => setMode('panel'));
    els.mask?.addEventListener('click', () => setMode('docked'));
    root.querySelector('#llmBtnClose')?.addEventListener('click', () => close());
    root.querySelector('#llmBtnDock')?.addEventListener('click', () => setMode('docked'));
    root.querySelector('#llmBtnMaximize')?.addEventListener('click', () => {
        setMode(mode === 'maximized' ? 'panel' : 'maximized');
    });
    root.querySelector('#llmBtnClearChat')?.addEventListener('click', () => {
        clearConversation(storageKey());
        messages = [];
        conversationId = `c_local_${Date.now()}`;
        renderThread(els.thread, messages);
        setStatus('已清空本机对话');
        if (els.promptMeta) els.promptMeta.textContent = '';
    });

    function storageKey() {
        return buildStorageKey(getUserId(), scope);
    }

    function reloadThreadForScope() {
        const stored = loadConversation(storageKey());
        conversationId = stored.conversation_id;
        messages = stored.messages || [];
        renderThread(els.thread, messages);
    }

    function remountChips() {
        mountChips(els.chips, {
            scope,
            disabled: busy || !canRun,
            onPick: (item, text) => {
                void submitQuestion({
                    text,
                    report_type: item.report_type,
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
                    report_type: 'auto',
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
            scope: {
                location: scope.location,
                year: scope.year,
                month: scope.month,
                vehicle_model: scope.vehicle_model,
                bom_version: scope.bom_version,
            },
            messages,
        });
        saveLastScope(scope);
    }

    function applyMode(next) {
        mode = next;
        const showPanel = mode === 'panel' || mode === 'maximized';
        const showDock = mode === 'docked';
        // panel / maximized 均可点外侧关闭；遮罩不压暗业务底（透明 + 轻模糊）
        const showMask = showPanel;

        els.panel?.classList.toggle('hidden', !showPanel);
        els.dock?.classList.toggle('hidden', !showDock);
        els.dock?.classList.toggle('flex', showDock);
        els.mask?.classList.toggle('hidden', !showMask);

        if (els.panel) {
            if (mode === 'maximized') {
                els.panel.className =
                    'fixed z-[110] flex flex-col overflow-hidden border border-[#2c2c2c] bg-[#121212] ' +
                    'left-4 right-4 top-16 bottom-4 w-auto h-auto shadow-[0_16px_48px_rgba(0,0,0,0.65)]';
            } else {
                els.panel.className =
                    'fixed z-[110] flex flex-col overflow-hidden border border-[#2c2c2c] bg-[#121212] ' +
                    'w-[min(380px,calc(100vw-1.5rem))] h-[min(560px,calc(100vh-5rem))] ' +
                    'right-4 bottom-4 shadow-[0_16px_48px_rgba(0,0,0,0.65)]';
            }
            if (!showPanel) els.panel.classList.add('hidden');
        }
    }

    function setMode(next) {
        applyMode(next);
    }

    /**
     * @param {{
     *   scope?: object,
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
        if (opts.scope) {
            scope = { ...scope, ...opts.scope };
            writeScope(els.scopeBar, scope);
            saveLastScope(scope);
        }
        if (opts.part_number) {
            scope = { ...scope, part_number: opts.part_number };
            writeScope(els.scopeBar, scope);
        }
        reloadThreadForScope();
        remountChips();
        setMode('panel');

        const promptId = opts.promptId || (opts.part_number ? 'Q51' : null);
        if (promptId) {
            const item = findPrompt(promptId);
            if (item) {
                const text = fillPromptTemplate(item.label, scope);
                if (opts.autoSend !== false) {
                    void submitQuestion({
                        text,
                        report_type: item.report_type,
                        audience: item.audience,
                        prompt_id: item.id,
                        needs_part_number: item.needs_part_number,
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
     *   report_type: string,
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

        scope = readScope(els.scopeBar);
        const scopeError = validateScope(scope);
        if (scopeError) {
            window.showToast?.(scopeError, 'warning');
            return;
        }

        let question = String(payload.text || '').trim();
        if (!question) return;

        if (payload.needs_part_number && !scope.part_number) {
            const part = window.prompt('请输入零件号');
            if (!part || !String(part).trim()) {
                window.showToast?.('零件号不能为空', 'warning');
                return;
            }
            scope = { ...scope, part_number: String(part).trim() };
            writeScope(els.scopeBar, scope);
            question = fillPromptTemplate(
                findPrompt(payload.prompt_id)?.label || question,
                scope,
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
            content: '分析中…',
            status: 'pending',
            created_at: new Date().toISOString(),
        };
        messages = [...messages, userMsg, assistantMsg];
        renderThread(els.thread, messages);
        persist();
        setBusy(true);
        setStatus('已提交分析…');

        try {
            const body = {
                report_type: payload.report_type || 'auto',
                user_question: question,
                scope: {
                    location: scope.location,
                    year: Number(scope.year),
                    month: Number(scope.month),
                    vehicle_model: scope.vehicle_model,
                    bom_version: scope.bom_version,
                    part_number: scope.part_number || null,
                },
                audience: payload.audience || null,
                prompt_id: payload.prompt_id || null,
                force_refresh: false,
            };

            const task = await createReport(body);
            const reportId = task.report_id;
            const taskId = task.task_id;
            assistantMsg.report_id = reportId;
            assistantMsg.task_id = taskId;

            let report = null;
            // 仅 succeeded 可跳过轮询；幂等命中 pending/running 仍须 poll
            const canSkipPoll =
                task.status === 'succeeded' ||
                (task.from_cache && task.status === 'succeeded');
            if (canSkipPoll) {
                setStatus(task.from_cache ? '命中缓存' : '已完成');
                report = await getReport(reportId);
            } else if (task.status === 'failed') {
                report = await getReport(reportId);
                throw new Error(report?.error_message || task.message || '分析失败');
            } else {
                if (pollAbort) pollAbort.abort();
                pollAbort = new AbortController();
                setStatus(task.message || '分析中…');
                await pollTask(taskId, {
                    signal: pollAbort.signal,
                    onProgress: (data) => {
                        const pct = data?.progress ?? 0;
                        const msg = data?.msg || '分析中…';
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

            assistantMsg.status = 'done';
            assistantMsg.content = report?.markdown_content || '（无正文）';
            assistantMsg.prompt_version = report?.metadata?.prompt_version || null;
            if (els.promptMeta) {
                els.promptMeta.textContent = assistantMsg.prompt_version || '';
            }
            setStatus(report?.metadata?.from_cache ? '完成（缓存）' : '完成');
            renderThread(els.thread, messages);
            persist();
        } catch (error) {
            assistantMsg.status = 'error';
            assistantMsg.content = error?.message || '分析失败';
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
        getScope: () => ({ ...scope }),
    };
}
