/**
 * 计算 / 生成 / 引擎运行历史的耗时展示（前端唯一入口）。
 *
 * 契约：
 * - 优先读后端 `duration_seconds`（与 VO mixin 对齐）。
 * - 仅当载荷未带该字段时，才用起止时间兜底推算（禁止各页面再抄一套）。
 * - 历史表固定三列：开始 / 结束 / 耗时；过程抽屉用 `formatTimingLine`。
 */

export function resolveDurationSeconds(row) {
    if (row == null) return null;
    if (Number.isFinite(row.duration_seconds)) {
        return Math.max(0, Math.round(Number(row.duration_seconds)));
    }
    if (!row.started_at || !row.finished_at) return null;
    const startMs = Date.parse(row.started_at);
    const endMs = Date.parse(row.finished_at);
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) {
        return null;
    }
    return Math.max(0, Math.round((endMs - startMs) / 1000));
}

export function formatDurationSeconds(row) {
    const seconds = resolveDurationSeconds(row);
    if (seconds == null) return '-';
    return `${seconds} 秒`;
}

export function formatTimingLine(row, formatDateTime) {
    const formatTs =
        typeof formatDateTime === 'function'
            ? formatDateTime
            : (value) => {
                  if (!value) return '-';
                  return String(value).replace('T', ' ').slice(0, 19);
              };
    const startText = formatTs(row?.started_at);
    const endText = formatTs(row?.finished_at);
    const durationText = formatDurationSeconds(row);
    if (startText === '-' && endText === '-' && durationText === '-') {
        return '';
    }
    return `开始 ${startText} · 结束 ${endText} · 耗时 ${durationText}`;
}
