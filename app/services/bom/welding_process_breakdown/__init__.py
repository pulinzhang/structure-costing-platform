"""BOM 焊接工艺拆解服务包

分层：
  parsers/…_parser.py          原文 → 单件工艺项（纯函数）
  bom_tree / fastener_check / rollup / evidence   生成与旁证辅助
  generate_service             从 BOM 生成
  audit_service                范围删除 / 审核 / 反审核
  export/                      L0 核对 Excel 导出（orchestrator 编排）
  service                      门面：查询 + 修改 + 委托上述服务
"""
