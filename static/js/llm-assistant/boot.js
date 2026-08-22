/**
 * 采购助理入口：就绪队列 + 顶栏挂载 + 权限门禁
 */

import { can } from '../permissions.js?v=9';
import { getUserSession } from '../features/login/index.js?v=14';
import { createShell } from './shell.js?v=15';

const QUEUE_KEY = '_q';

function installStub() {
    if (window.LlmAssistant && window.LlmAssistant.__ready) {
        return;
    }
    const existingQueue = Array.isArray(window.LlmAssistant?.[QUEUE_KEY])
        ? window.LlmAssistant[QUEUE_KEY]
        : [];

    window.LlmAssistant = {
        [QUEUE_KEY]: existingQueue,
        __ready: false,
        open(...args) {
            this[QUEUE_KEY].push(['open', args]);
        },
        close(...args) {
            this[QUEUE_KEY].push(['close', args]);
        },
        setMode(...args) {
            this[QUEUE_KEY].push(['setMode', args]);
        },
    };
}

installStub();

let booted = false;

/**
 * 登录 /me 刷新权限后调用
 */
export function bootLlmAssistant() {
    if (booted) return;
    booted = true;

    const canView = can('op:llm-analysis:view') || can('op:llm-analysis:run');
    const canRun = can('op:llm-analysis:run');

    const headerRight = document.querySelector('.page-header-right');
    let entryHost = document.getElementById('llmAssistantEntry');
    if (!entryHost && headerRight) {
        entryHost = document.createElement('span');
        entryHost.id = 'llmAssistantEntry';
        entryHost.className = 'inline-flex';
        const helpLink = headerRight.querySelector('a[href="/helper/"]');
        if (helpLink) {
            headerRight.insertBefore(entryHost, helpLink);
        } else {
            const topActions = headerRight.querySelector('#topActions');
            if (topActions?.nextSibling) {
                headerRight.insertBefore(entryHost, topActions.nextSibling);
            } else {
                headerRight.prepend(entryHost);
            }
        }
    }

    if (!canView) {
        if (entryHost) entryHost.innerHTML = '';
        window.LlmAssistant = {
            __ready: true,
            [QUEUE_KEY]: [],
            open() {},
            close() {},
            setMode() {},
        };
        return;
    }

    const shell = createShell({
        canView,
        canRun,
        entryHost,
        getUserId: () => {
            const session = getUserSession();
            return session?.user_id || session?.id || session?.username || 'anon';
        },
    });

    const queued = Array.isArray(window.LlmAssistant?.[QUEUE_KEY])
        ? [...window.LlmAssistant[QUEUE_KEY]]
        : [];

    window.LlmAssistant = {
        __ready: true,
        [QUEUE_KEY]: [],
        open: (...args) => shell.open(...args),
        close: (...args) => shell.close(...args),
        setMode: (...args) => shell.setMode(...args),
        getMode: () => shell.getMode(),
    };

    queued.forEach(([method, args]) => {
        const fn = window.LlmAssistant[method];
        if (typeof fn === 'function') {
            try {
                fn(...args);
            } catch (error) {
                console.warn('[llm-assistant] flush queue failed', method, error);
            }
        }
    });
}
