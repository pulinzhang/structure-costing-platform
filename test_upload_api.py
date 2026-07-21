"""
测试冲压文件上传 API
"""
import requests
import sys
from pathlib import Path

# 配置
BASE_URL = "http://localhost:8000"
FILE_PATH = Path(r"D:\高考\stamping-costing-platform\excelSample\副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsx")

def test_upload():
    print("=" * 60)
    print("开始测试冲压文件上传 API")
    print("=" * 60)
    
    # 1. 检查服务器状态
    print("\n[1] 检查服务器状态...")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"    服务器状态: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print("    错误: 无法连接到服务器！请确保 uvicorn 已启动。")
        return
    except Exception as e:
        print(f"    错误: {e}")
        return
    
    # 2. 检查上传路由是否存在
    print("\n[2] 检查上传页面...")
    try:
        resp = requests.get(f"{BASE_URL}/upload/stamping/", timeout=5)
        print(f"    页面状态: {resp.status_code}")
        if resp.status_code == 200:
            print("    上传页面可访问")
        else:
            print(f"    警告: 页面返回非 200 状态码")
    except Exception as e:
        print(f"    错误: {e}")
    
    # 3. 检查文件是否存在
    print("\n[3] 检查文件...")
    if FILE_PATH.exists():
        print(f"    文件存在: {FILE_PATH}")
        print(f"    文件大小: {FILE_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"    错误: 文件不存在: {FILE_PATH}")
        return
    
    # 4. 执行上传
    print("\n[4] 执行文件上传...")
    print(f"    车型: T28")
    print(f"    版本: 1.0")
    
    try:
        with open(FILE_PATH, "rb") as f:
            files = {"file": (FILE_PATH.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {
                "vehicle_model": "T28",
                "version": "1.0"
            }
            
            print("    正在发送请求...")
            resp = requests.post(
                f"{BASE_URL}/upload/stamping/",
                files=files,
                data=data,
                timeout=120  # 2分钟超时
            )
            
            print(f"\n    响应状态码: {resp.status_code}")
            print(f"    响应头: Content-Type={resp.headers.get('Content-Type', 'N/A')}")
            
            # 5. 检查响应
            print("\n[5] 检查响应内容...")
            try:
                json_resp = resp.json()
                print(f"    响应 JSON: {json_resp}")
                
                if json_resp.get("success"):
                    print("\n    ✅ 上传成功!")
                    print(f"    零件数: {json_resp.get('data', {}).get('parts_count', 'N/A')}")
                    print(f"    工序数: {json_resp.get('data', {}).get('processes_count', 'N/A')}")
                else:
                    print("\n    ❌ 上传失败!")
                    print(f"    错误信息: {json_resp.get('detail', 'N/A')}")
            except Exception as e:
                print(f"    响应不是 JSON 格式: {e}")
                print(f"    原始响应: {resp.text[:500]}")
                
    except Exception as e:
        print(f"\n    请求错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. 检查日志文件
    print("\n[6] 检查日志文件...")
    logs_dir = Path(r"D:\高考\stamping-costing-platform\logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            print(f"    发现 {len(log_files)} 个日志文件:")
            for lf in log_files:
                print(f"      - {lf.name} ({lf.stat().st_size} bytes)")
                # 显示最后几行
                try:
                    content = lf.read_text(encoding="utf-8")
                    lines = content.strip().split("\n")
                    print(f"        内容 ({len(lines)} 行):")
                    for line in lines[-5:]:
                        print(f"          {line[:100]}")
                except Exception as e:
                    print(f"        读取错误: {e}")
        else:
            print("    logs 目录为空")
    else:
        print("    logs 目录不存在")
    
    # 7. 检查数据库
    print("\n[7] 检查数据库...")
    db_path = Path(r"D:\高考\stamping-costing-platform\data\stamping_costing.db")
    if db_path.exists():
        print(f"    数据库存在: {db_path}")
        print(f"    大小: {db_path.stat().st_size / 1024:.2f} KB")
        
        # 使用 sqlite3 检查记录数
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查零件表
        cursor.execute("SELECT COUNT(*) FROM stamping_parts")
        parts_count = cursor.fetchone()[0]
        print(f"    stamping_parts 表记录数: {parts_count}")
        
        # 检查工序表
        cursor.execute("SELECT COUNT(*) FROM stamping_processes")
        processes_count = cursor.fetchone()[0]
        print(f"    stamping_processes 表记录数: {processes_count}")
        
        conn.close()
    else:
        print("    数据库不存在")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_upload()
