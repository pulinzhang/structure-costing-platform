/**
 * 对话历史 — 本机浮窗会话缓存（非服务端分析历史权威源）
 */

const STORAGE_PREFIX = 'llm_chat_v1';
const MAX_MESSAGES = 50;

/**
 * @param {string|number|null|undefined} userId
 * @returns {string}
 */
export function buildStorageKey(userId) {
    return `${STORAGE_PREFIX}:${userId || 'anon'}:nl`;
}

/**
 * @param {string} key
 * @returns {{ version: number, conversation_id: string, updated_at: string, messages: object[] }}
 */
export function loadConversation(key) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) {
            return emptyConversation();
        }
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.messages)) {
            return emptyConversation();
        }
        return {
            version: 1,
            conversation_id: parsed.conversation_id || `c_local_${Date.now()}`,
            updated_at: parsed.updated_at || new Date().toISOString(),
            messages: parsed.messages.slice(-MAX_MESSAGES),
        };
    } catch {
        return emptyConversation();
    }
}

export function emptyConversation() {
    return {
        version: 1,
        conversation_id: `c_local_${Date.now()}`,
        updated_at: new Date().toISOString(),
        messages: [],
    };
}

/**
 * @param {string} key
 * @param {object} conversation
 */
export function saveConversation(key, conversation) {
    const payload = {
        version: 1,
        conversation_id: conversation.conversation_id || `c_local_${Date.now()}`,
        updated_at: new Date().toISOString(),
        messages: Array.isArray(conversation.messages)
            ? conversation.messages.slice(-MAX_MESSAGES)
            : [],
    };
    try {
        localStorage.setItem(key, JSON.stringify(payload));
    } catch (error) {
        // QuotaExceeded：淘汰最旧一半后再试一次
        if (payload.messages.length > 10) {
            payload.messages = payload.messages.slice(Math.floor(payload.messages.length / 2));
            try {
                localStorage.setItem(key, JSON.stringify(payload));
            } catch {
                console.warn('[llm-assistant] localStorage save failed', error);
            }
        }
    }
    return payload;
}

/**
 * @param {string} key
 */
export function clearConversation(key) {
    try {
        localStorage.removeItem(key);
    } catch {
        /* ignore */
    }
}
