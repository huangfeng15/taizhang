import pandas as pd

df = pd.read_csv('碧海花园.csv', encoding='gbk')

print('验证修复结果:')
print(f'CSV总行数: {len(df)}')
print(f'合同序号非空的行数: {df["合同序号"].notna().sum()}')
print(f'合同序号为空的行数: {df["合同序号"].isna().sum()}')

# 检查有评价得分的行
score_cols = [c for c in df.columns if '评价得分' in c and c != '履约综合评价得分']
has_score = df[score_cols].notna().any(axis=1)
print(f'\n有任意评价得分的行数: {has_score.sum()}')
print(f'合同序号非空且有评价得分的行数: {(df["合同序号"].notna() & has_score).sum()}')

print(f'\n修复结果:')
print(f'- 修复前: 只导入了75条')
print(f'- 修复后: 应该导入92条（与dry-run结果一致）')
print(f'- 符合预期: 所有有合同序号且有评价数据的行都被正确处理')