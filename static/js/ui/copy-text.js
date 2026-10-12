/**
 * 把纯文本写入剪贴板。
 * 局域网 http 没有 Clipboard API，在点击当次用 textarea 写入。
 *
 * @param {string} text
 * @returns {Promise<boolean>}
 */
export function copyPlainText(text) {
    const value = String(text ?? '');
    if (!value) return Promise.resolve(false);
    if (window.isSecureContext && navigator.clipboard?.writeText) {
        return navigator.clipboard.writeText(value).then(() => true, () => false);
    }
    return Promise.resolve(copyWithTextarea(value));
}

const COPY_IDLE = '复制';
const COPY_DONE = '已复制';

/** 复制元素里已经显示的正文，并在按钮上短暂显示「已复制」。 */
export async function copyElementText(body, button) {
    const value = body?.textContent || '';
    if (!value) return;
    const copied = await copyPlainText(value);
    if (!copied) {
        window.showToast?.('复制失败', 'error');
        return;
    }
    if (!button) return;
    button.textContent = COPY_DONE;
    window.setTimeout(() => {
        if (button.isConnected && button.textContent === COPY_DONE) {
            button.textContent = COPY_IDLE;
        }
    }, 1600);
}

function copyWithTextarea(value) {
    const active = document.activeElement;
    const area = document.createElement('textarea');
    area.value = value;
    area.setAttribute('readonly', '');
    area.setAttribute('aria-hidden', 'true');
    area.style.fontSize = '12pt';
    area.style.border = '0';
    area.style.padding = '0';
    area.style.margin = '0';
    area.style.position = 'absolute';
    area.style.left = '-9999px';
    area.style.top = `${window.pageYOffset || document.documentElement.scrollTop}px`;
    document.body.appendChild(area);
    area.focus({ preventScroll: true });
    area.select();
    let copied = false;
    try {
        copied = document.execCommand('copy');
    } catch (_) {
        copied = false;
    }
    area.remove();
    if (active instanceof HTMLElement && active.isConnected) {
        active.focus({ preventScroll: true });
    }
    return copied;
}
