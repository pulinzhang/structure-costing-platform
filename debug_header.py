import openpyxl

wb = openpyxl.load_workbook('excelSample/副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsm', data_only=True)
ws = wb.active

val = ws.cell(5, 14).value
print(f"raw type: {type(val)}")
print(f"raw value: {repr(val)}")

if isinstance(val, bytes):
    print(f"as gbk: {val.decode('gbk')}")
    print(f"as utf-8: {val.decode('utf-8', errors='replace')}")
    print(f"as latin-1: {val.decode('latin-1')}")
else:
    print(f"as str: {str(val)}")
