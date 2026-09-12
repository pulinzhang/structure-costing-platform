# 废料月度销售价格 Service（`yishiyiyi/scrap_price`）

> 一事一议 · 冲压废料月度销售价业务层  
> 路径：`app/services/yishiyiyi/scrap_price/`

采用「根门面 + 按关注点子包」组织，与 `yishiyiyi/policy`、`yishiyiyi/base_price` 一致。

---

## 1. 业务范围

| 能力 | 说明 |
|------|------|
| 整月矩阵 CRUD | 按类别取数；保存/复制/删除只覆盖当前类别；行=已启用基地 |
| 月份导航 | 已维护月份摘要、筛选项 |
| Excel 导出 | 按年宽表（大盘价 / 扣费 / 净价公式） |

**对外入口**：

```python
from app.services.yishiyiyi.scrap_price import (
    StampingScrapPriceService,
    StampingScrapPriceExportService,
)
```

无 Excel 导入子包：本切片为人工按月录入，不是文件灌库。

---

## 2. 为什么这样组织

1. **按关注点分包**  
   整月业务规则与宽表 Excel 版式无关：改矩阵逻辑看 `crud/`，改表样看 `export/excel_exporter.py`。

2. **门面只做委托**  
   `StampingScrapPriceService` 不写业务细节；下载接口走 `StampingScrapPriceExportService`。

3. **查询与 Excel 生成分离**  
   `export_service` 拉年/月数据；`excel_exporter` 负责合并格、公式与边框。

4. **仍遵守项目分层**  
   写库走 Repository；Router 不直接碰 Repository。

---

## 3. 目录结构

```text
app/services/yishiyiyi/scrap_price/
├── README.md
├── __init__.py
├── scrap_price_service.py          # 薄门面
├── crud/
│   └── scrap_price_crud.py         # 整月取数/保存/复制/删除
└── export/
    ├── export_service.py           # 查库 + 调导出器
    └── excel_exporter.py           # 宽表 openpyxl
```

---

## 4. 依赖方向

```text
Router
  ├── StampingScrapPriceService → crud
  └── StampingScrapPriceExportService → exporter
        │
        ▼
repositories.yishiyiyi.scrap_price
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `crud/` | 月表 VO、净价计算、replace/copy/delete | xlsx |
| `export/` | 按年取数、宽表样式与公式 | 写库 |

---

## 5. 关键业务约定

- 基地行 = `LocationService.list_enabled`；废止固定 6 行。
- `save_month` / `copy_month` / `delete_month`：只覆盖 `year + month + scrap_category`。
- 导出：按钢材料 / 铝材分块；列随已登记基地变。

---

## 6. 职责

| 模块 | 职责 |
|------|------|
| `crud/scrap_price_crud.py` | 月表字段 / 复制校验 |
| `export/export_service.py` | 导出取数范围 |
| `export/excel_exporter.py` | 宽表版式 / 公式 |

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/scrap_price/` |
| Repository | `app/repositories/yishiyiyi/scrap_price/` |
| 前端 | `static/js/features/yishiyiyi/scrap-price/` |
| API 前缀 | `/api/yishiyiyi/scrap-price` |
| 对照结构 | `app/services/yishiyiyi/base_price/` |
