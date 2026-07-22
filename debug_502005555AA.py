"""通过 API 上传并验证"""
import requests
import os

API_BASE = "http://localhost:8000/api"

# 上传文件
file_path = "excelSample/副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsx"
print("上传文件...")
with open(file_path, "rb") as f:
    files = {"file": (os.path.basename(file_path), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"vehicle_model": "T28", "version": "1.0"}
    resp = requests.post(f"{API_BASE}/stamping/upload", files=files, data=data)

print(f"上传状态: {resp.status_code}")
if resp.status_code == 200:
    result = resp.json()
    print(f"零件数: {result.get('data', {}).get('parts_count')}")
    print(f"工序数: {result.get('data', {}).get('processes_count')}")

    # 查询数据库
    import sqlite3
    conn = sqlite3.connect("data/stamping_costing.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.process_seq, p.process_order, p.process_code
        FROM stamping_processes p
        JOIN stamping_parts pt ON p.part_id = pt.id
        WHERE pt.part_number = '502005555AA'
        ORDER BY p.process_order
    """)
    rows = cursor.fetchall()
    print(f"\n数据库中 502005555AA 的工序: {len(rows)} 道")
    for row in rows:
        print(f"  ID={row[0]}, seq={row[1]}, order={row[2]}, code={row[3]}")

    conn.close()
else:
    print(f"上传失败: {resp.text}")