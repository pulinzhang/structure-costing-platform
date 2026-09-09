"""
采购对象清单服务包

分层：
  labels.py              对人展示文案（种类 / 分区）
  classify.py            树上分类（纯函数）
  generate_service.py    从材料清单生成
  generate_log_service.py  生成批次日志
    audit_service.py       确认 / 按范围审核、反审核、删除
    supplier_template.py   导入窄表第一页 / 填写说明
    supplier_upload_service.py  下载模板 + 上传改供应商
    export.py              Excel 导出
  mapping.py             ORM → VO
  service.py             门面：查询 + 委托上述服务
"""

from app.services.bom.procurement_object.service import BomProcurementObjectService

__all__ = ["BomProcurementObjectService"]
