# 材料变更 — 5 展示

> 落地：**第五刀（最后）。** 零件明细带回冲压历史。改图把冲压历史抄到新零件。  
> 依赖：[03-menu-list-rollback.md](03-menu-list-rollback.md)。  
> 目录：[README.md](README.md)

---

## 1. 展示（冲压零件详情）

不另开接口。`GET /api/stamping/parts/{part_id}` 在工序旁边带回 `material_changes`。空列表 = 没有材料变更。不要用工艺 `material` 和解析值相不相等去猜。

明细列：有效时间、变更前材料、变更前料厚、变更后材料、变更后料厚。按生效月升序。有效止 = 下一刀前一月或「未结束」。版本、冲压工厂、原件不在这里。原件只在材料变更列表，下载仍是 `GET /uploads/{id}/file`。

读权限跟零件详情。回滚仍只在材料变更列表。禁止按一条历史删。抽屉无删除钮。

零件列表「材料」列仍是投产字。核价走 `list_materials_as_of`。

---

## 2. 改图抄历史

新工艺行插入后，设计变更调 `StampingMaterialChangeService`，把旧零件历史整表插入新零件。旧零件历史留下。设计变更效果链接记下新历史 id。材料变更仍只写自己的 Excel，写入和删除历史调同一个服务。读工艺身份调 `StampingDesignChangeService`。两条通道互不调用。

先材料、后改图：新号工艺 `material` 仍是旧号那一格投产字。历史整表插到新零件，不把解析值写入工艺 `material`。

禁止：设变 import 本通道；本通道 import 设变；改 `clone_revise_part_payload` 去写历史；把解析值写入新号工艺 `material`。回滚设变按这些 id 删新零件上抄来的历史，不删旧零件历史，不删本通道的行。

---

## 3. 本刀验收

- [ ] 零件详情 `material_changes`：无历史为空；导入 06 后有一条；两本回滚完再空
- [ ] 改图 115AA→AB：AB 工艺仍是投产字；AB 的 `material_changes` 与 AA 相同；AA 的历史仍在。回滚设变后 AB 为空，AA 仍在
- [ ] 不改 `app/common/`、不改核价引擎
