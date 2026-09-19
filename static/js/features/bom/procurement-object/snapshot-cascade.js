/**
 * 采购对象 · snapshot 头级联（生成页 / 供应商批传共用）。
 *
 * 后端属 BOM 上级域：GET /api/bom/filters/cascade?version_source=snapshot。
 * 禁止自建第二套 cascade；禁止默认 L0（会露出 EC）。以生成页为准。
 */

const CASCADE_API = '/api/bom/filters/cascade';

/**
 * @param {{
 *   state: { location: string, vehicleModel: string, bomVersion: string },
 *   locationId: string,
 *   modelId: string,
 *   versionId: string,
 * }} options
 */
export async function loadSnapshotCascade(options) {
    const { state, locationId, modelId, versionId } = options;
    try {
        const params = { version_source: 'snapshot' };
        if (state.location) params.location = state.location;
        if (state.vehicleModel) params.vehicle_model = state.vehicleModel;
        const res = await HttpClient.get(CASCADE_API, { params });
        const data = res.data || {};
        const locations = data.locations || [];
        const vehicleModels = data.vehicle_models || [];
        const bomVersions = data.bom_versions || [];

        if (state.location && !locations.includes(state.location)) {
            state.location = '';
            state.vehicleModel = '';
            state.bomVersion = '';
        }
        if (state.vehicleModel && !vehicleModels.includes(state.vehicleModel)) {
            state.vehicleModel = '';
            state.bomVersion = '';
        }
        if (state.bomVersion && !bomVersions.includes(state.bomVersion)) {
            state.bomVersion = '';
        }
        if (!state.location && locations.length === 1) {
            state.location = locations[0];
            return loadSnapshotCascade(options);
        }
        if (state.location && !state.vehicleModel && vehicleModels.length === 1) {
            state.vehicleModel = vehicleModels[0];
            return loadSnapshotCascade(options);
        }
        if (
            state.location
            && state.vehicleModel
            && !state.bomVersion
            && bomVersions.length === 1
        ) {
            state.bomVersion = bomVersions[0];
        }
        fillSelect(locationId, locations, state.location);
        fillSelect(modelId, vehicleModels, state.vehicleModel);
        fillSelect(versionId, bomVersions, state.bomVersion);
    } catch (error) {
        console.error('加载 BOM snapshot 级联筛选失败', error);
    }
}

function fillSelect(id, values, selected, emptyLabel = '请选择') {
    const el = document.getElementById(id);
    if (!el) return;
    let html = `<option value="">${emptyLabel}</option>`;
    (values || []).forEach((item) => {
        const mark = item === selected ? ' selected' : '';
        html += `<option value="${esc(item)}"${mark}>${esc(item)}</option>`;
    });
    el.innerHTML = html;
    if (selected && (values || []).includes(selected)) {
        el.value = selected;
    } else {
        el.value = '';
    }
}
