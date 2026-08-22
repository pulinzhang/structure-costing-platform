/**
 * 对话历史 — 仅 localStorage（C8）
 */

const STORAGE_PREFIX = 'llm_chat_v1';
const MAX_MESSAGES = 50;

/**
 * @param {object} scope
 * @returns {string}
 */
export function buildScopeKey(scope) {
    const location = String(scope?.location || '').trim();
    const year = String(scope?.year || '').trim();
    const month = String(scope?.month || '').trim();
    const vehicleModel = String(scope?.vehicle_model || '').trim();
    const bomVersion = String(scope?.bom_version || '').trim();
    return `${location}|${year}|${month}|${vehicleModel}|${bomVersion}`;
}

/**
 * @param {string|number|null|undefined} userId
 * @param {object} scope
 * @returns {string}
 */
export function buildStorageKey(userId, scope) {
    return `${STORAGE_PREFIX}:${userId || 'anon'}:${buildScopeKey(scope)}`;
}

/**
 * @param {string} key
 * @returns {{ version: number, conversation_id: string, scope: object, updated_at: string, messages: object[] }}
 */
export function loadConversation(key) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) {
            return emptyConversation(null);
        }
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.messages)) {
            return emptyConversation(null);
        }
        return {
            version: 1,
            conversation_id: parsed.conversation_id || `c_local_${Date.now()}`,
            scope: parsed.scope || null,
            updated_at: parsed.updated_at || new Date().toISOString(),
            messages: parsed.messages.slice(-MAX_MESSAGES),
        };
    } catch {
        return emptyConversation(null);
    }
}

/**
 * @param {object|null} scope
 */
export function emptyConversation(scope) {
    return {
        version: 1,
        conversation_id: `c_local_${Date.now()}`,
        scope: scope || null,
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
        scope: conversation.scope || null,
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

const LAST_SCOPE_KEY = 'llm_assistant_last_scope_v1';

/**
 * @returns {object|null}
 */
export function loadLastScope() {
    try {
        const raw = localStorage.getItem(LAST_SCOPE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
        return null;
    }
}

/**
 * @param {object} scope
 */
export function saveLastScope(scope) {
    try {
        localStorage.setItem(LAST_SCOPE_KEY, JSON.stringify(scope));
    } catch {
        /* ignore */
    }
}
