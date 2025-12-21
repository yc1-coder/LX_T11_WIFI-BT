import pandas as pd
import re
import os

# 读取配置文件
columns_config = pd.read_excel('Setting.xlsx', sheet_name='Sheet1')
columns_config.columns = range(len(columns_config.columns))

# 获取第一列的匹配规则
target_patterns = columns_config.iloc[:, 0].dropna().tolist()
print("需要匹配的列模式:", target_patterns)

# 读取Willy.xlsx数据
df = pd.read_excel('Willy.xlsx')

# 获取前几列作为基础信息（例如前3列）
base_columns = df.columns[:19].tolist()  # 可根据实际需要调整列数

# 创建输出文件夹
output_folder = "extracted_data"
os.makedirs(output_folder, exist_ok=True)

# 为每个模式创建单独的文件
for pattern in target_patterns:
    matched_columns = []

    # 查找匹配的列
    for column in df.columns:
        if re.search(pattern.replace('*', '.*'), str(column), re.IGNORECASE):
            matched_columns.append(column)

    # 如果找到匹配的列，则保存到对应文件
    if matched_columns:
        # 组合基础列和匹配列
        selected_columns = base_columns + matched_columns
        extracted_data = df[selected_columns]

        # 生成文件名（使用模式名作为文件名）
        filename = pattern.replace('*', '_') + ".csv"
        output_file = os.path.join(output_folder, filename)

        # 保存为CSV格式
        extracted_data.to_csv(output_file, index=False)
        print(f"已保存: {output_file}")
        print(f"  包含列: {selected_columns}")
    else:
        print(f"未找到匹配模式 '{pattern}' 的列")
