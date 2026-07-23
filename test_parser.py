import sys
sys.path.insert(0, '.')
from app.parsers import parse_stamping_excel

# 直接测试
result = parse_stamping_excel('excelSample/副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsx')
parts = result.parts
processes = result.processes

print(f'\n最终结果:')
print(f'零件数: {len(parts)}')
print(f'工序数: {len(processes)}')

# 检查零件是否重复（现在用对象属性）
part_nums = [p.part_number for p in parts]
unique_parts = set(part_nums)
print(f'不重复零件数: {len(unique_parts)}')

# 显示前10个零件
print('\n前10个零件:')
for i, p in enumerate(parts[:10]):
    print(f"  {i+1}. {p.part_number} - {p.part_name}")

# 检查目标零件的工序数量
print('\n\n=== 检查目标零件的工序数量 ===')
target_parts = ['502005555AA', '501008902AA']

# 按零件号统计工序
process_by_part = {}
for proc in processes:
    if proc.part_number not in process_by_part:
        process_by_part[proc.part_number] = []
    process_by_part[proc.part_number].append(proc)

for part_no in target_parts:
    procs = process_by_part.get(part_no, [])
    print(f'\n零件 {part_no}: {len(procs)} 个工序')
    for proc in procs:
        print(f'  - OP{proc.process_seq}: {proc.process_code}')
