/**
 * AsyncTask 轮询
 */

import { getTaskProgress } from '../api.js';

const DEFAULT_INTERVAL_MS = 1500;
const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;

/**
 * @param {string} taskId
 * @param {{
 *   intervalMs?: number,
 *   timeoutMs?: number,
 *   onProgress?: (data: object) => void,
 *   signal?: AbortSignal,
 * }} [options]
 * @returns {Promise<object>}
 */
export function pollTask(taskId, options = {}) {
    const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
    const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const onProgress = options.onProgress;
    const signal = options.signal;
    const startedAt = Date.now();

    return new Promise((resolve, reject) => {
        let timer = null;
        let inFlight = false;

        const cleanup = () => {
            if (timer != null) {
                clearTimeout(timer);
                timer = null;
            }
            if (signal) {
                signal.removeEventListener('abort', onAbort);
            }
        };

        const onAbort = () => {
            cleanup();
            reject(new Error('已取消轮询'));
        };

        if (signal) {
            if (signal.aborted) {
                onAbort();
                return;
            }
            signal.addEventListener('abort', onAbort, { once: true });
        }

        const tick = async () => {
            if (inFlight) {
                timer = setTimeout(tick, intervalMs);
                return;
            }
            if (Date.now() - startedAt > timeoutMs) {
                cleanup();
                reject(new Error('分析超时，请稍后重试'));
                return;
            }

            inFlight = true;
            try {
                const data = await getTaskProgress(taskId);
                if (typeof onProgress === 'function') {
                    onProgress(data);
                }
                const status = String(data?.status || '').toLowerCase();
                if (status === 'completed' || status === 'succeeded') {
                    cleanup();
                    resolve(data);
                    return;
                }
                if (status === 'failed') {
                    cleanup();
                    reject(new Error(data?.msg || '分析失败'));
                    return;
                }
                timer = setTimeout(tick, intervalMs);
            } catch (error) {
                cleanup();
                reject(error);
            } finally {
                inFlight = false;
            }
        };

        tick();
    });
}
