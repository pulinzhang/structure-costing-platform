/**
 * 采购助理 API — 仅封装 /api/llm/*
 */

/**
 * @param {object} payload
 * @returns {Promise<object>}
 */
export async function createReport(payload) {
    const res = await HttpClient.post('/api/llm/reports', payload);
    return res.data;
}

/**
 * @param {number|string} reportId
 * @returns {Promise<object>}
 */
export async function getReport(reportId) {
    const res = await HttpClient.get(`/api/llm/reports/${encodeURIComponent(String(reportId))}`);
    return res.data;
}

/**
 * @param {string} taskId
 * @returns {Promise<object>}
 */
export async function getTaskProgress(taskId) {
    const res = await HttpClient.get(`/api/llm/tasks/${encodeURIComponent(taskId)}`);
    return res.data;
}
