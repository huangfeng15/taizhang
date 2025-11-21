import pandas as pd

df = pd.read_csv('碧海花园.csv', encoding='gbk')

print('CSV文件统计:')
print(f'总行数: {len(df)}')
print(f'有末次评价得分: {df["末次评价得分"].notna().sum()}')

# 检查有年度评价的行
annual_cols = [c for c in df.columns if '年度评价得分' in c]
has_annual = df[annual_cols].notna().any(axis=1).sum()
print(f'有年度评价得分: {has_annual}')

# 检查有任意评价得分的行（不包括履约综合评价得分）
score_cols = [c for c in df.columns if '评价得分' in c and c != '履约综合评价得分']
has_any_score = df[score_cols].notna().any(axis=1).sum()
print(f'有任意评价得分（应该全部导入）: {has_any_score}')

print(f'\n修复前只导入了75条，修复后应该导入 {has_any_score} 条')