# 材料变更 — 测试配套

> 不写业务代码。落地各刀单测/接口测按本表。成功样表在 [samples/](samples/README.md)。负例用测试里现场改格子，不必另提交一堆 xlsx。

目录：[README.md](README.md)

---

## 成功两本（按序）

1. `t13j-2026-06-material-change.xlsx` → 芜湖 / T13J / 2025 / 06  
2. `t13j-2026-07-material-change.xlsx` → 芜湖 / T13J / 2025 / 07  

---

## 负例（整本拒、零切点）

| 改法 | 期望码（中文全文见 02） |
|------|-------------------------|
| 表名改成「工程变更单」 | `ECM_SHEET_REQUIRED` |
| 第 1 行写标题、表头在第 2 行 | `ECM_HEADER` |
| `2026年13月` | `ECM_EFFECTIVE_FORMAT` |
| `MAT-202507` 配 06 月 | `ECM_VERSION_FORMAT` |
| DC01→DC01 | `ECM_AFTER_EQUALS_BEFORE` |
| 变更前料厚改成 `1.6`（工艺仍 1.5） | `ECM_BEFORE_THICKNESS` |
| 变更后料厚改成 `2.0`（相对 1.5 超过 20%） | `ECM_THICKNESS_DELTA` |
| 料厚写成文字「1.5」，或数字 `1.555` | `ECM_THICKNESS_FORMAT` |
| 互换性多一个空格 | `ECM_CELL_NOT_EXACT` |
| 零件号改成数字格 | `ECM_CELL_TYPE` |
| 只传 07、不传 06 | `ECM_BEFORE_MATERIAL` |
| 06 成功后 07 变更前改 DC01 | `ECM_BEFORE_MATERIAL` |
| 再传一份 MAT-202506 | `ECM_VERSION_DUPLICATE` |
| 先回滚 06、07 还在 | `ECM_ROLLBACK_BLOCKED` |
| 行上写拼焊件号 / 利废件 | `ECM_TAILOR_WELD_FORBIDDEN` / `ECM_OFFAL_FORBIDDEN` |
| 05 月改图已成功，06 月零件号改成 `551003095AA` | `ECM_PART_NOT_AS_OF` |
| 有切点后 SOP 改工艺材料再传下一本 | `ECM_PROCESS_MATERIAL_CHANGED` |
| 失败头点删除 | 头消失、切点仍为零、再下原件 404 |
| 振华已成功 MAT-202506，全鑫同项目同月再传同版本 | 过（版本占用按厂） |
| MIXED：工艺生效月不等于本本切点月 | 不命中 `ECM_MIXED_WITH_REVISE` |

---

## 生失效与标识

导入 06+07 后、以及两本都回滚后：115AA 生失效四列与导入前逐格相同；records 空。两本都回滚后，那两个头 id 不能再下载，盘上文件还在。只回滚 07 时，留下的 06 仍能下载。
