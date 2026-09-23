# 材料变更 — 3 菜单、列表、回滚、权限

> 落地：**第三刀。** 侧栏、上传/列表页、整本回滚、溯源、删工艺挡、权限。  
> 依赖：[02-upload-gates.md](02-upload-gates.md)。不要改钢材/零件价。  
> 目录：[README.md](README.md)

---

## 1. 菜单与前端路径

现网：一级 `menu:engineering-change`；二级分组 `menu:engineering-change-design-group`。

本刀加第二个二级分组，**不要新一级**。前端现网占位是：

`static/js/features/engineering-change/material-change/`

（不是 `static/js/pages/material-change/`。）hash：`#/engineering-change-material-upload`、`#/engineering-change-material-list`（不要带斜杠的 hash）。打开页再拉目录。

| catalog | 文案 |
|---------|------|
| `menu:engineering-change-material-group` | 材料变更（分组） |
| `menu:engineering-change-material-upload` | 上传 |
| `menu:engineering-change-material-list` | 列表 |

`op:`：

| 码 | 用途 |
|----|------|
| `op:engineering-change-material-upload:view` | 打开上传页 |
| `op:engineering-change-material-upload:upload` | 下载模板 / 提交上传 |
| `op:engineering-change-material-list:view` | 列表、下载原件 |
| `op:engineering-change-material-list:delete` | 整本回滚 |

不复用设计变更的 upload/delete 码。新建用户 **不要** 默认给材料变更。已有设计变更菜单的用户 **不要** 自动补材料变更。管理员仍是 `*`。启动补齐：若用户已有材料上传或列表菜单，补上分组码（对称设计变更 `ensure_bootstrap`）。

变更记录只挂本通道 `GET /parts/{part_id}/records`。前端零件页若要打开，多请求这一条，**不改冲压 Router/VO**。读权限：`op:stamping-parts:view` 或本通道 list:view。

---

## 2. API（前缀 `/api/engineering-change/material`，整数 id）

| 方法 | 路径 | 权限 |
|------|------|------|
| GET | `/template` | upload:upload |
| POST | `/upload` | upload:upload |
| GET | `/upload/tasks/{task_id}` | upload:view 或 upload:upload 或 list:view |
| GET | `/uploads` | list:view（分页：`page`+`size`；筛基地、项目、年、月、版本、状态） |
| GET | `/uploads/{id}/file` | list:view 下载原件 |
| DELETE | `/uploads/{id}` | list:delete：**成功头 = 整本回滚**；**失败头 = 删头**（无切点）。原件留盘 |
| GET | `/parts/{part_id}/records` | 冲压零件列表查看码 |

列表粒度 = **变更单行**（与设计变更同一纪律：一本成功 Excel 出 N 行）。失败、进行中没有切点时仍出一行头。列对齐「工程变更单（材质）」：基地、项目/生效、冲压工厂、版本、零件号、零件名称、变更前/后材料、变更前/后料厚、互换性；另加源文件、上传人、上传时间、整本状态。改图抄来的行（`copied_from_order_id` 非空）不进这张表。失败头出现在列表。操作：查看（抽屉里下载原件）；成功头与失败头都是删除，成功删除 = 整本回滚。

DTO/VO 字段小写下划线。禁止 `data=` 解匿名元组。

---

## 3. 回滚与删除失败头

列表删的仍是 **一本上传头**。拦更晚刀时按 **基地 + 冲压工厂 + 项目 + 零件号**，不是「这个项目还有任意更晚一本」，也不是「另一厂同号更晚就拦」。

对本本每一个切点（含改图抄到新号、仍挂这本 `upload_log_id` 的行）：同 `location` + `stamping_supplier` + `vehicle_model` + `part_number` 是否还有 **生效月更晚** 的成功切点。有 → `ECM_ROLLBACK_BLOCKED`，整本不删。没有 → 可以删。抄行用新号身份参加检查：新号自己还有更晚刀，就不能回滚抄出它的那本，因为回滚会把抄行一起删掉。

例：06 本 115AA+116AA，07 本只有 115AA → 回滚 06 拒（115AA 还有更晚）。07 本全是别的号、115/116 没有更晚刀 → 可以回滚 06。

删序：链接 → 切点（本头 `upload_log_id` 下全部，含后来改图抄出去、仍挂这本 `upload_log_id` 的行）→ 头。不留 `rolled_back`。**不改工艺行任何列**。对身份 **调冲压服务**再读一遍（行还在、id 不变），禁止本通道自己 UPDATE 冲压表。

该零件相关材料变更 **全部回滚完**（该号切点条数为 0）后必须同时成立：

| 项 | 必须 |
|----|------|
| 生失效四列 | 与第一刀上传前逐格相同 |
| `material` / `version` | 仍是投产字（115AA：`DC01` / `V3-01`） |
| `list_materials_as_of` 任意年月 | 材料 = 工艺 `material`（切点已删光） |
| records | 空 |

回滚后下游结果表故意留下，不代重算。见 [04-steel-and-part-cost.md](04-steel-and-part-cost.md)。

只回滚 07、06 仍在：07 月解析回到 DC03。可立刻再传一份 `MAT-202507`（变更前仍须 DC03）。回滚不删溯源原件，见 §4。

**失败头可以删。** 无切点，只删头。pending 头不能删，走 `ECM_PENDING_VERSION`，等任务结束。删失败头后 `GET /uploads/{id}/file` **404**（id 是头 id）。验收「仍能下」= **删除前** 列表能下。

---

## 4. 原件与删挡

原件落在本通道目录，头上 `upload_file_id`。下载只走 `GET /uploads/{id}/file` 和 records「原件」。**禁止改** `file_trace` 切片。回滚不盘删原件。失败头可下载、可删头。

有切点时删工艺：数据库 FK `IntegrityError`，现网删挡不认识这张外键，文案是「这次没有删成。」不要改冲压删挡文案。

---

## 5. 本刀验收

- [ ] 工程变更下两个二级；权限树出现上表码；无菜单用户侧栏不出现
- [ ] 模板下载、异步上传、失败头在列表、成功可回滚
- [ ] 导入 06 再 07：115AA 生失效四列与导入前相同
- [ ] 先回滚 07 再回滚 06：生失效仍相同；解析 = DC01；records 空
- [ ] 只回滚 07：06 仍在；07 月解析 = DC03；可再传 07 样表
- [ ] 07 未删时回滚含 115AA 的 06 → `ECM_ROLLBACK_BLOCKED`；07 全是别的零件号时可以回滚 06
- [ ] 失败头可删除；删后列表没有这头，本通道下载 404
- [ ] 删 115AA 工艺：有切点则 IntegrityError，冲压删挡文案不为本通道改字
- [ ] 06 成功：列表能下载原件，hash 与磁盘一致
- [ ] 负例失败头：切点为零；失败头可删；删后下载 404
- [ ] 回滚 07：材料变更列表没了 07 头；07 的头 id 不能再下载，盘上文件还在；留下的 06 仍能下载；再传 07 不顶掉上一份盘上文件
