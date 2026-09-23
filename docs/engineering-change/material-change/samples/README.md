# 材料变更样表

测试配套，按这个顺序传：

| 序 | 文件 | 上传页 | 内容 |
|----|------|--------|------|
| 1 | [t13j-2026-06-material-change.xlsx](t13j-2026-06-material-change.xlsx) | 芜湖 / T13J / 2026 / 06 | `MAT-202606`，DC01→DC03，料厚 1.5→1.5 |
| 2 | [t13j-2026-07-material-change.xlsx](t13j-2026-07-material-change.xlsx) | 芜湖 / T13J / 2026 / 07 | `MAT-202607`，**DC03→DC01**（再变回去），料厚 1.5→1.5 |

07 月变更前必须是库里最新 DC03。没有 06 先成功，07 过不了门禁。

重写：

```
python -X utf8 docs/engineering-change/material-change/samples/build_t13j_2026_06.py
python -X utf8 docs/engineering-change/material-change/samples/build_t13j_2026_07.py
```

负例不要另存一堆 xlsx，测试里改格子即可，清单见 [../06-test.md](../06-test.md)。
