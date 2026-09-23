# 材料变更 — 5 展示、改图抄历史

> 落地：**第五刀（最后）。** 本通道 records；改图 persist **调本通道**抄切点历史。  
> 依赖：[03-menu-list-rollback.md](03-menu-list-rollback.md)。  
> 依赖：[03-menu-list-rollback.md](03-menu-list-rollback.md)。  
> 目录：[README.md](README.md)

---

## 1. 展示（本通道 API）

变更记录只挂本通道：`GET /api/engineering-change/material/parts/{part_id}/records`。用 `part_id` **调冲压服务**读出身份（**行 id 不变**），再查切点。

空列表 = 没有材料变更。不要用工艺 `material` 和解析值相不相等去猜。

抽屉列（缺一不可）：变更版本、有效时间、变更前材料、变更前料厚、变更后材料、变更后料厚、冲压工厂、原件（本通道 `upload_file_id` 下载）。按生效月升序。有效止 = 下一刀前一月或「未结束」。

读权限：`op:stamping-parts:view` 或本通道 list:view。回滚仍只在材料变更列表。禁止按一条切点删。列表删的是一本上传头，不支持单条切点回滚。抽屉无删除钮。无 list:view 时抽屉不显示下载。

当月材料：变更记录给人看；核价走 `list_materials_as_of` 返回的字。零件列表「材料」列仍是投产字（本通道不改列表 VO）。原件：records 带文件名；下载走 `GET /uploads/{id}/file`。

---

## 2. 改图：工艺仍抄旧号；切点历史由本通道抄

原则：**抄就是全抄，包括变更。** 不准把解析后的 DC03 写进新号工艺 `material`。

一级/二级改图 persist 在现网抄工艺整行 **之后**，只加一次调用：

`MaterialChangeService.copy_cutovers(from_part_id, to_part_id)`

本通道内部再 **调冲压服务**读新旧行身份，然后：

1. 旧号上全部成功切点（含已经是抄来的）按生效月升序。  
2. 对新号各插一行：`part_number` / `source_part_id` / `part_name` 换新号；其余切点字段照抄；`copied_from_order_id` = 刚抄的那一行 id；`excel_row` 空。  
3. 新号 UNIQUE 按新零件号。二次改图 AB→AC 时，AB 上从 AA 抄来的刀也要再到 AC。

禁止改 `clone_revise_part_payload` 去写切点表。禁止改图 UPDATE 旧号切点的零件号。

回滚设计变更（删 AB）：设计变更回滚 **调本通道** `delete_copied_cutovers(part_id=AB)`。只删抄行。AA 原切点不动。

回滚材料变更 06 本：仍按第 3 刀整本删切点（含抄到 AB 的 06 刀）；拦更晚刀按基地+冲压工厂+项目+零件号。AB 上若还有更晚刀，回滚 06 会把抄行一起删掉，所以拦住。回滚过程 **调冲压服务**核对身份，不写工艺列。

例：只导入 06 后 08 月 115AA→115AB：AB 工艺 DC01，带 06 抄行。再导入 07 后同一改图：AB 带 06、07 两刀抄行。下游计算不在本通道改。

---

## 3. 本刀验收

- [ ] `GET .../parts/{id}/records`：无切点空表；导入 06 后有 MAT-202506；两本回滚完再空
- [ ] 改图 115AA→AB：AB 工艺 DC01；records 有抄来的刀；回滚设计变更后抄行删除、AA 原切点仍在
- [ ] copy 只发生在本通道 Service；不改 `app/common/`、不改核价引擎
