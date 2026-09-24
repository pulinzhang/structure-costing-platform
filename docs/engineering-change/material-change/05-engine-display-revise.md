# 材料变更 — 5 展示

> 落地：**第五刀（最后）。** 本通道 records。改图不抄切点。  
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

## 2. 改图不抄切点

设计变更只抄工艺行。本通道只写自己 Excel 落下的切点。两条通道互不调用。

先材料、后改图：新号工艺 `material` 仍是旧号那一格投产字。旧号切点留在旧号。新号要切材料，另传本通道 Excel。

禁止：设变 import 本通道；本通道 import 设变；改 `clone_revise_part_payload` 去写切点；把解析值写入新号工艺 `material`。回滚设变不删本通道的行。

---

## 3. 本刀验收

- [ ] `GET .../parts/{id}/records`：无切点空表；导入 06 后有 MAT-202506；两本回滚完再空
- [ ] 改图 115AA→AB：AB 工艺仍是投产字；AB 的 records 为空；AA 的切点仍在。回滚设变不删材料变更行
- [ ] 不改 `app/common/`、不改核价引擎
