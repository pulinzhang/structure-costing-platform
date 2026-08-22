/**
 * 将 GET /reports/{id} 响应写入助理消息体
 */

/**
 * @param {object} msg
 * @param {object} report
 * @returns {object}
 */
export function applyReportToMessage(msg, report) {
    const snapshot = report?.snapshot && typeof report.snapshot === 'object'
        ? report.snapshot
        : null;
    const actions = Array.isArray(report?.actions) && report.actions.length
        ? report.actions
        : (Array.isArray(snapshot?.actions) ? snapshot.actions : []);

    msg.status = 'done';
    msg.content = report?.markdown_content || '（无正文）';
    msg.report_id = report?.report_id ?? msg.report_id;
    msg.task_id = report?.task_id ?? msg.task_id;
    msg.prompt_version = report?.metadata?.prompt_version || null;
    msg.from_cache = Boolean(report?.metadata?.from_cache);
    msg.generated_at = report?.metadata?.generated_at || null;
    msg.resolved_report_type = report?.resolved_report_type || null;
    msg.scope = report?.scope || null;
    msg.snapshot = snapshot;
    msg.actions = actions;
    msg.has_data = report?.metadata?.has_data !== false;
    msg.data_message = report?.metadata?.data_message || snapshot?.meta?.data_message || null;
    msg.user_question = report?.user_question || null;
    return msg;
}
