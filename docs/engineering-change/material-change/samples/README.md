# 材料变更样表（芜湖 T13J）

今天反复测，就这一处。开发服务开在 `http://127.0.0.1:8000`，仓库根目录执行：

```
python -X utf8 docs/engineering-change/material-change/samples/run_wuhu_t13j_browser_test.py
```

脚本会先清掉库里已有的 `MAT-202607`、`MAT-202606`，再跑负例、成功两本、回滚顺序。账号 `admin` / `admin123`。

| 序 | 文件 | 上传页 | 内容 |
|----|------|--------|------|
| 1 | [t13j-2026-06-material-change.xlsx](t13j-2026-06-material-change.xlsx) | 芜湖 / T13J / 2026 / 06 | `MAT-202606`，DC01→DC03，料厚 1.5→1.5 |
| 2 | [t13j-2026-07-material-change.xlsx](t13j-2026-07-material-change.xlsx) | 芜湖 / T13J / 2026 / 07 | `MAT-202607`，DC03→DC01，料厚 1.5→1.5 |

07 月变更前必须是库里最新 DC03。没有 06 先成功，07 过不了门禁。

重写样表：

```
python -X utf8 docs/engineering-change/material-change/samples/build_t13j_2026_06.py
python -X utf8 docs/engineering-change/material-change/samples/build_t13j_2026_07.py
```

负例不另存 xlsx。脚本改格子写到本目录 `_cases/`，跑完删除。清单见 [../06-test.md](../06-test.md)。
