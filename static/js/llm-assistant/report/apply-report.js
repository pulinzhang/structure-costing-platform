/**
 * 将 GET /reports/{id} 响应写入助理消息体
 */

/**
 * @param {object} msg
 * @param {object} report
 * @returns {object}
 */
export function applyReportToMessage(msg, report) {
    msg.status = 'done';
    msg.content = report?.markdown_content || '（无正文）';
    msg.report_id = report?.report_id ?? msg.report_id;
    msg.task_id = report?.task_id ?? msg.task_id;
    msg.from_cache = Boolean(report?.metadata?.from_cache);
    msg.generated_at = report?.metadata?.generated_at || null;
    msg.prompt_version = report?.metadata?.prompt_version || null;
    msg.resolved_report_type = report?.resolved_report_type || null;
    msg.scope = report?.scope || null;
    if (report?.carry) {
        msg.carry = report.carry;
    }
    msg.user_question = report?.user_question || null;
    return msg;
}
