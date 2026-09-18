"""
采购对象清单服务包

改前先读：docs/bom/bom-procurement-objects-design.md（尤其 §14：列表档案、只认 L0 树根、设变插行）。
指定对方：docs/bom/bom-procurement-object-supplier-design.md。

分层：
  labels.py              对人展示文案（种类 / 分区）
  classify.py            树上分类（纯函数）
  row_write.py           分类行 → Write（generate / 合册插行共用；始终 pending 审核）
  generate_service.py    从材料清单生成
  generate_log_service.py  生成批次日志
  insert_service.py      合册种树后本树插行（不 commit）
  audit_service.py       确认 / 按范围审核、反审核、删除
  supplier_template.py   导入窄表第一页 / 填写说明
  supplier_upload_service.py  下载模板 + 上传改供应商
  export.py              Excel 导出门面
  columns.py / styles.py / values.py / workbook.py / export_service.py
  mapping.py             ORM → VO；树根期；scope_from_query
  service.py             门面：查询 + 委托上述服务
"""

from app.services.bom.procurement_object.service import BomProcurementObjectService

__all__ = ["BomProcurementObjectService"]
