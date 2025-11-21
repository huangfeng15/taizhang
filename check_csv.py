import pandas as pd

df = pd.read_csv('碧海花园.csv', encoding='gbk')
print(f'总行数: {len(df)}')
print(f'\n末次评价得分非空的行数: {df["末次评价得分"].notna().sum()}')
print(f'末次评价得分为空的行数: {df["末次评价得分"].isna().sum()}')

print(f'\n年度评价列非空统计:')
for col in [c for c in df.columns if '年度评价得分' in c]:
    print(f'{col}: {df[col].notna().sum()}')

print(f'\n过程评价列非空统计:')
for col in [c for c in df.columns if '过程评价得分' in c]:
    print(f'{col}: {df[col].notna().sum()}')

# 检查有任意评价得分的行
print(f'\n详细分析:')
score_cols = ['末次评价得分'] + [c for c in df.columns if '年度评价得分' in c or '过程评价得分' in c]
df['has_any_score'] = df[score_cols].notna().any(axis=1)
print(f'至少有一个评价得分的行数: {df["has_any_score"].sum()}')

# 显示末次评价为空但有其他评价的行
no_last_but_has_others = df[df['末次评价得分'].isna() & df['has_any_score']]
print(f'\n没有末次评价但有其他评价的行数: {len(no_last_but_has_others)}')
if len(no_last_but_has_others) > 0:
    print('示例（前5行）:')
    print(no_last_but_has_others[['序号', '合同序号', '末次评价得分'] + [c for c in df.columns if '年度评价得分' in c or '过程评价得分' in c]].head())