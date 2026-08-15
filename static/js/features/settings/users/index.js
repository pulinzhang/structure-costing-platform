/**
 * Users Page
 * 用户管理 —对接 /api/users CRUD
 *
 * 抽屉式交互：
 * - 编辑/新增  →editDrawer
 * - 修改密码  →passwordDrawer
 * - 删除确认  →deleteDrawer
 */

import { usersTemplate, renderTableRows, renderPagination } from './template.js?v=3';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../page-size.js?v=2';

const usersState = {
    records: [],
    total: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    keyword: '',
    username: '',
    realName: '',
    isActive: null,
    isLoading: false,
};

const API_BASE = '/api/users';
const DRAWER_ANIMATION_MS = 300;

function openDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.style.display = 'flex';
    if (backdrop) backdrop.style.display = 'block';
    void drawer.offsetWidth;
    drawer.classList.remove('translate-x-full');
    drawer.classList.add('translate-x-0');
}

function closeDrawer(drawerId, backdropId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById(backdropId);
    if (!drawer) return;
    drawer.classList.remove('translate-x-0');
    drawer.classList.add('translate-x-full');
    setTimeout(() => {
        drawer.style.display = 'none';
        if (backdrop) backdrop.style.display = 'none';
    }, DRAWER_ANIMATION_MS);
}

function init() {
    loadData();
    bindEvents();
    bindPageSizeSelect('usersPageSize', {
        getSize: () => usersState.pageSize,
        setSize: (size) => {
            usersState.pageSize = size;
        },
        onChange: () => loadData(1),
    });
    const btnAdd = document.getElementById('btnAddUser');
    if (btnAdd && typeof can === 'function' && !can('op:settings-users:create')) {
        btnAdd.classList.add('hidden');
    }
}

async function loadData(page = 1) {
    if (usersState.isLoading) return;
    usersState.isLoading = true;

    const tableBody = document.getElementById('usersTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const totalCountPagination = document.getElementById('totalCountPagination');
    const paginationBtns = document.getElementById('paginationBtns');

    if (tableBody) tableBody.innerHTML = '';
    if (emptyState) emptyState.classList.add('hidden');
    if (loadingState) loadingState.classList.remove('hidden');

    try {
        const params = {
            page,
            size: usersState.pageSize,
        };
        if (usersState.keyword) params.keyword = usersState.keyword;
        if (!usersState.keyword && usersState.username) params.username = usersState.username;
        if (!usersState.keyword && usersState.realName) params.real_name = usersState.realName;
        if (usersState.isActive !== null && usersState.isActive !== '') {
            params.is_active = usersState.isActive;
        }

        const res = await HttpClient.get(API_BASE, { params });
        const pageResult = res.data || {};

        usersState.records = pageResult.items || [];
        usersState.total = pageResult.total || 0;
        usersState.page = pageResult.page || page;
        usersState.totalPages = pageResult.total_pages || 1;

        if (tableBody) {
            if (usersState.records.length === 0) {
                tableBody.innerHTML = '';
                if (emptyState) emptyState.classList.remove('hidden');
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                tableBody.innerHTML = renderTableRows(usersState.records);
                bindTableRowEvents();
            }
        }

        updateOverviewStats(pageResult.filters?.summary || null);

        if (totalCountPagination) {
            totalCountPagination.textContent = `全${usersState.total} 条`;
        }
        if (paginationBtns) {
            paginationBtns.innerHTML = renderPagination(usersState.page, usersState.totalPages);
        }
    } catch (error) {
        console.error('加载用户失败:', error);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-[#9e9e9e] text-xs">
                        加载数据失败，请重试
                    </td>
                </tr>
            `;
        }
        usersState.total = 0;
        usersState.records = [];
        updateOverviewStats(null);
    } finally {
        usersState.isLoading = false;
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function updateOverviewStats(summary) {
    const statTotal = document.getElementById('statTotalUsers');
    const statActive = document.getElementById('statActiveUsers');
    const statAdmin = document.getElementById('statAdminUsers');
    const data = summary && typeof summary === 'object' ? summary : {};

    if (statTotal) statTotal.textContent = String(usersState.total || 0);
    if (statActive) statActive.textContent = String(data.active_count ?? 0);
    if (statAdmin) statAdmin.textContent = String(data.admin_count ?? 0);
}

function bindTableRowEvents() {
    document.querySelectorAll('.edit-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = usersState.records.find((r) => r.id === id);
            if (record) openEditDrawer(record);
        });
    });

    document.querySelectorAll('.password-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = usersState.records.find((r) => r.id === id);
            if (record) openPasswordDrawer(record);
        });
    });

    document.querySelectorAll('.delete-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = usersState.records.find((r) => r.id === id);
            if (record) openDeleteDrawer(record);
        });
    });

    document.querySelectorAll('.grant-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            const id = parseInt(row.dataset.id, 10);
            const record = usersState.records.find((r) => r.id === id);
            if (record) openGrantDrawer(record);
        });
    });
}

function bindEvents() {
    const btnAdd = document.getElementById('btnAddUser');
    if (btnAdd) {
        btnAdd.addEventListener('click', () => openAddDrawer());
    }

    const btnFilter = document.getElementById('btnFilter');
    if (btnFilter) {
        btnFilter.addEventListener('click', () => {
            applyFilters();
            loadData(1);
        });
    }

    const keywordInput = document.getElementById('filterKeyword');
    if (keywordInput) {
        keywordInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                applyFilters();
                loadData(1);
            }
        });
    }

    const filterIsActive = document.getElementById('filterIsActive');
    if (filterIsActive) {
        filterIsActive.addEventListener('change', () => {
            applyFilters();
            loadData(1);
        });
    }

    bindEditDrawerEvents();
    bindPasswordDrawerEvents();
    bindDeleteDrawerEvents();
    bindGrantDrawerEvents();
    bindPaginationEvents();
}

function applyFilters() {
    const keywordInput = document.getElementById('filterKeyword');
    const isActiveSelect = document.getElementById('filterIsActive');

    usersState.keyword = keywordInput ? keywordInput.value.trim() : '';
    usersState.username = '';
    usersState.realName = '';

    const activeValue = isActiveSelect ? isActiveSelect.value : '';
    if (activeValue === 'true') usersState.isActive = true;
    else if (activeValue === 'false') usersState.isActive = false;
    else usersState.isActive = null;
}

function bindEditDrawerEvents() {
    const closeBtn = document.getElementById('closeEditDrawer');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const backdrop = document.getElementById('editDrawerBackdrop');
    const submitBtn = document.getElementById('submitEditBtn');

    const close = () => closeDrawer('editDrawer', 'editDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

    if (submitBtn) {
        submitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await saveUser();
        });
    }
}

function bindPasswordDrawerEvents() {
    const closeBtn = document.getElementById('closePasswordDrawer');
    const cancelBtn = document.getElementById('cancelPasswordBtn');
    const backdrop = document.getElementById('passwordDrawerBackdrop');
    const submitBtn = document.getElementById('submitPasswordBtn');

    const close = () => closeDrawer('passwordDrawer', 'passwordDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

    if (submitBtn) {
        submitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await savePassword();
        });
    }
}

function bindDeleteDrawerEvents() {
    const closeBtn = document.getElementById('closeDeleteDrawer');
    const cancelBtn = document.getElementById('cancelDeleteBtn');
    const backdrop = document.getElementById('deleteDrawerBackdrop');
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    const close = () => closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);

    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            const id = parseInt(document.getElementById('deleteUserId')?.value, 10);
            if (id) await deleteUser(id);
        });
    }
}

function bindPaginationEvents() {
    const container = document.getElementById('paginationBtns');
    if (container) {
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('.page-btn');
            if (btn && !btn.disabled) {
                const page = parseInt(btn.dataset.page, 10);
                if (page) loadData(page);
            }
        });
    }
}

function openAddDrawer() {
    const title = document.getElementById('editDrawerTitle');
    const userId = document.getElementById('editUserId');
    const usernameInput = document.getElementById('editUsername');
    const passwordGroup = document.getElementById('editPasswordGroup');
    const passwordInput = document.getElementById('editPassword');
    const usernameHint = document.getElementById('editUsernameHint');
    const form = document.getElementById('editForm');

    if (title) title.textContent = '新增用户';
    if (userId) userId.value = '';
    if (form) form.reset();
    if (usernameInput) {
        usernameInput.readOnly = false;
        usernameInput.classList.remove('opacity-60', 'cursor-not-allowed');
    }
    if (passwordGroup) passwordGroup.classList.remove('hidden');
    if (passwordInput) passwordInput.required = true;
    if (usernameHint) usernameHint.classList.add('hidden');

    const isActiveSelect = document.getElementById('editIsActive');
    if (isActiveSelect) isActiveSelect.value = 'true';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (usernameInput) setTimeout(() => usernameInput.focus(), DRAWER_ANIMATION_MS);
}

function openEditDrawer(record) {
    const title = document.getElementById('editDrawerTitle');
    const userId = document.getElementById('editUserId');
    const usernameInput = document.getElementById('editUsername');
    const passwordGroup = document.getElementById('editPasswordGroup');
    const passwordInput = document.getElementById('editPassword');
    const usernameHint = document.getElementById('editUsernameHint');

    if (title) title.textContent = '编辑用户';
    if (userId) userId.value = record.id;
    if (usernameInput) {
        usernameInput.value = record.username || '';
        usernameInput.readOnly = true;
        usernameInput.classList.add('opacity-60', 'cursor-not-allowed');
    }
    if (passwordGroup) passwordGroup.classList.add('hidden');
    if (passwordInput) {
        passwordInput.value = '';
        passwordInput.required = false;
    }
    if (usernameHint) usernameHint.classList.remove('hidden');

    const realNameInput = document.getElementById('editRealName');
    const departmentInput = document.getElementById('editDepartment');
    const emailInput = document.getElementById('editEmail');
    const phoneInput = document.getElementById('editPhone');
    const isActiveSelect = document.getElementById('editIsActive');

    if (realNameInput) realNameInput.value = record.real_name || '';
    if (departmentInput) departmentInput.value = record.department || '';
    if (emailInput) emailInput.value = record.email || '';
    if (phoneInput) phoneInput.value = record.phone || '';
    if (isActiveSelect) isActiveSelect.value = record.is_active === false ? 'false' : 'true';

    openDrawer('editDrawer', 'editDrawerBackdrop');
    if (realNameInput) setTimeout(() => realNameInput.focus(), DRAWER_ANIMATION_MS);
}

function openPasswordDrawer(record) {
    const userId = document.getElementById('passwordUserId');
    const usernameLabel = document.getElementById('passwordUsername');
    const form = document.getElementById('passwordForm');
    const newPassword = document.getElementById('newPassword');

    if (userId) userId.value = record.id;
    if (usernameLabel) usernameLabel.textContent = record.username || '';
    if (form) form.reset();
    if (userId) userId.value = record.id;
    if (usernameLabel) usernameLabel.textContent = record.username || '';

    openDrawer('passwordDrawer', 'passwordDrawerBackdrop');
    if (newPassword) setTimeout(() => newPassword.focus(), DRAWER_ANIMATION_MS);
}

function openDeleteDrawer(record) {
    const userId = document.getElementById('deleteUserId');
    const usernameLabel = document.getElementById('deleteUsername');
    if (userId) userId.value = record.id;
    if (usernameLabel) usernameLabel.textContent = record.username || '';
    openDrawer('deleteDrawer', 'deleteDrawerBackdrop');
}

function emptyToNull(value) {
    const text = (value || '').trim();
    return text === '' ? null : text;
}

async function saveUser() {
    const userId = document.getElementById('editUserId')?.value;
    const username = document.getElementById('editUsername')?.value?.trim();
    const password = document.getElementById('editPassword')?.value;
    const realName = emptyToNull(document.getElementById('editRealName')?.value);
    const department = emptyToNull(document.getElementById('editDepartment')?.value);
    const email = emptyToNull(document.getElementById('editEmail')?.value);
    const phone = emptyToNull(document.getElementById('editPhone')?.value);
    const isActive = document.getElementById('editIsActive')?.value === 'true';

    try {
        if (userId) {
            await HttpClient.put(`${API_BASE}/${userId}`, {
                real_name: realName,
                email,
                phone,
                department,
                is_active: isActive,
            });
            showToast('更新成功', 'success');
        } else {
            if (!username || username.length < 2) {
                showToast('请填写登录账号（至少 2 个字符）', 'warning');
                return;
            }
            if (!password || password.length < 4) {
                showToast('请填写登录密码（至少 4 个字符）', 'warning');
                return;
            }
            await HttpClient.post(API_BASE, {
                username,
                password,
                real_name: realName,
                email,
                phone,
                department,
                is_active: isActive,
            });
            showToast('创建成功', 'success');
        }

        closeDrawer('editDrawer', 'editDrawerBackdrop');
        loadData(userId ? usersState.page : 1);
    } catch (error) {
        console.error('保存用户失败:', error);
    }
}

async function savePassword() {
    const userId = document.getElementById('passwordUserId')?.value;
    const password = document.getElementById('newPassword')?.value;
    const confirm = document.getElementById('confirmPassword')?.value;

    if (!userId) return;
    if (!password || password.length < 4) {
        showToast('新密码至少4 个字符, 'warning');
        return;
    }
    if (password !== confirm) {
        showToast('两次输入的密码不一自, 'warning');
        return;
    }

    try {
        await HttpClient.put(`${API_BASE}/${userId}/password`, { password });
        showToast('密码已更新, 'success');
        closeDrawer('passwordDrawer', 'passwordDrawerBackdrop');
    } catch (error) {
        console.error('修改密码失败:', error);
    }
}

async function deleteUser(id) {
    try {
        await HttpClient.delete(`${API_BASE}/${id}`);
        showToast('删除成功', 'success');
        closeDrawer('deleteDrawer', 'deleteDrawerBackdrop');

        const nextPage = usersState.records.length <= 1 && usersState.page > 1
            ? usersState.page - 1
            : usersState.page;
        loadData(nextPage);
    } catch (error) {
        console.error('删除用户失败:', error);
    }
}

function bindGrantDrawerEvents() {
    const closeBtn = document.getElementById('closeGrantDrawer');
    const cancelBtn = document.getElementById('cancelGrantBtn');
    const backdrop = document.getElementById('grantDrawerBackdrop');
    const submitBtn = document.getElementById('submitGrantBtn');
    const close = () => closeDrawer('grantDrawer', 'grantDrawerBackdrop');

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            await saveGrant();
        });
    }
}

async function openGrantDrawer(record) {
    const userIdInput = document.getElementById('grantUserId');
    const nameEl = document.getElementById('grantUsername');
    const container = document.getElementById('grantTreeContainer');
    if (userIdInput) userIdInput.value = String(record.id);
    if (nameEl) nameEl.textContent = record.username || '';
    if (container) {
        container.innerHTML = `
            <div class="flex items-center justify-center py-10">
                <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
            </div>`;
    }
    openDrawer('grantDrawer', 'grantDrawerBackdrop');

    try {
        const [treeRes, codesRes] = await Promise.all([
            HttpClient.get('/api/permissions/tree'),
            HttpClient.get(`${API_BASE}/${record.id}/permissions`),
        ]);
        const tree = treeRes.data || [];
        const checked = new Set(codesRes.data || []);
        if (container) {
            container.innerHTML = renderPermissionTree(tree, checked);
            bindGrantTreeEvents(container);
        }
    } catch (error) {
        console.error('加载权限树失败', error);
        if (container) {
            container.innerHTML = `<p class="text-[11px] text-[#ef5350]">加载权限树失败</p>`;
        }
    }
}

function renderPermissionTree(nodes, checked, depth = 0) {
    if (!Array.isArray(nodes) || nodes.length === 0) return '';
    return nodes.map((node) => {
        const code = node.code || '';
        const isMandatory = node.mandatory === true;
        const isChecked = isMandatory || checked.has(code);
        const pad = depth * 16;
        const childrenHtml = renderPermissionTree(node.children || [], checked, depth + 1);
        const typeHint = node.type === 'op' ? '操作' : (node.type === 'group' ? '分组' : '菜单');
        return `
            <div class="grant-node" data-code="${esc(code)}" data-mandatory="${isMandatory ? '1' : '0'}">
                <label class="flex items-center gap-2 py-1.5 hover:bg-[#ffffff]/[0.02] cursor-pointer ${isMandatory ? 'opacity-70' : ''}"
                       style="padding-left:${pad}px">
                    <input type="checkbox" class="grant-check accent-[#d32f2f]"
                           data-code="${esc(code)}"
                           ${isChecked ? 'checked' : ''}
                           ${isMandatory ? 'disabled' : ''}>
                    <span class="text-[11px] ${isMandatory ? 'text-[#888888]' : 'text-[#c0c0c0]'}">${esc(node.label || code)}</span>
                    <span class="text-[9px] text-[#484848] uppercase tracking-wider">${typeHint}${isMandatory ? ' · 必选' : ''}</span>
                </label>
                ${childrenHtml}
            </div>`;
    }).join('');
}

function bindGrantTreeEvents(container) {
    container.querySelectorAll('.grant-check').forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            const node = checkbox.closest('.grant-node');
            if (!node) return;
            if (checkbox.checked) {
                checkAncestors(node);
                checkDescendants(node, true);
            } else {
                checkDescendants(node, false);
            }
        });
    });
}

function checkAncestors(node) {
    let parent = node.parentElement?.closest('.grant-node');
    while (parent) {
        const box = parent.querySelector(':scope > label > .grant-check');
        if (box && !box.disabled) box.checked = true;
        parent = parent.parentElement?.closest('.grant-node');
    }
}

function checkDescendants(node, checked) {
    node.querySelectorAll('.grant-node .grant-check').forEach((box) => {
        if (box.disabled) return;
        box.checked = checked;
    });
}

async function saveGrant() {
    const userId = parseInt(document.getElementById('grantUserId')?.value, 10);
    if (!userId) return;
    const codes = [];
    document.querySelectorAll('#grantTreeContainer .grant-check').forEach((box) => {
        if (box.checked || box.disabled) {
            const code = box.getAttribute('data-code');
            if (code) codes.push(code);
        }
    });
    try {
        await HttpClient.put(`${API_BASE}/${userId}/permissions`, { codes });
        showToast('授权已保存, 'success');
        closeDrawer('grantDrawer', 'grantDrawerBackdrop');
    } catch (error) {
        console.error('保存授权失败:', error);
    }
}

export const pageConfig = {
    render: usersTemplate,
    init: () => init(),
};
