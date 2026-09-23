/**
 * 材料变更原件下载。列表和零件详情共用这一处。
 */

const API = '/api/engineering-change/material';

/**
 * @param {number} uploadLogId
 * @param {string} [fallbackName]
 */
export async function downloadMaterialChangeFile(uploadLogId, fallbackName) {
    const fallback = fallbackName || 'material-change.xlsx';
    const { blob, filename } = await HttpClient.download(
        `${API}/uploads/${uploadLogId}/file`,
        { defaultFilename: fallback },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || fallback;
    link.click();
    URL.revokeObjectURL(url);
}
