import sys
sys.path.insert(0, '.')
from app.parsers import parse_stamping_excel

# 直接测试
parts, processes = parse_stamping_excel('excelSample/副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsm')

print(f'\n最终结果:')
print(f'零件数: {len(parts)}')
print(f'工序数: {len(processes)}')

# 检查零件是否重复
part_nums = [p['part_number'] for p in parts]
unique_parts = set(part_nums)
print(f'不重复零件数: {len(unique_parts)}')

# 显示前10个零件
print('\n前10个零件:')
for i, p in enumerate(parts[:10]):
    print(f"  {i+1}. {p['part_number']}")
