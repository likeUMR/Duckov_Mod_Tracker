"""
合并old_data文件夹中的旧数据到mod_stats.csv
处理时间戳格式统一、数据清理和去重
"""
import pandas as pd
import os
import re
from datetime import datetime
from mod_config import MODS

OLD_DATA_DIR = 'old_data'
CURRENT_DATA_FILE = 'mod_stats.csv'
BACKUP_FILE = 'mod_stats_backup.csv'

def extract_mod_id_from_filename(filename):
    """
    从文件名提取mod_id
    文件名格式: steam_mod_{Mod名称}_{hash}.csv
    """
    # 移除扩展名和前缀
    name_part = filename.replace('steam_mod_', '').replace('.csv', '')
    
    # 文件名到mod名称的映射（通过文件名中的关键词匹配）
    # Better_Appearance_Pr -> Better Appearance Preset
    # Hide_Body_Equipment -> Hide Body Equipment
    # Hide_The_Pet -> Hide The Pet
    
    name_mapping = {
        'Better_Appearance_Pr': 'Better Appearance Preset',
        'Hide_Body_Equipment': 'Hide Body Equipment',
        'Hide_The_Pet': 'Hide The Pet'
    }
    
    # 查找匹配的mod名称
    for file_key, mod_name in name_mapping.items():
        if file_key in name_part:
            # 在MODS中查找对应的mod_id
            for mod_id, mod_info in MODS.items():
                if mod_info['name'] == mod_name:
                    return mod_id
    
    return None

def normalize_timestamp(timestamp_str):
    """
    统一时间戳格式为 YYYY-MM-DD HH:MM:SS
    处理两种格式：
    1. 2025/11/1 17:18 -> 2025-11-01 17:18:00
    2. 2025-11-01 20:54:02 -> 保持不变
    """
    if pd.isna(timestamp_str) or timestamp_str == '':
        return None
    
    timestamp_str = str(timestamp_str).strip()
    
    # 处理斜杠格式: 2025/11/1 17:18
    if '/' in timestamp_str:
        try:
            # 替换斜杠为横杠，并补齐日期格式
            parts = timestamp_str.split(' ')
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else '00:00'
            
            # 解析日期部分: 2025/11/1 -> 2025-11-01
            date_parts = date_part.split('/')
            year = date_parts[0]
            month = date_parts[1].zfill(2)
            day = date_parts[2].zfill(2)
            
            # 解析时间部分，如果没有秒则添加:00
            time_parts = time_part.split(':')
            hour = time_parts[0].zfill(2)
            minute = time_parts[1].zfill(2) if len(time_parts) > 1 else '00'
            second = time_parts[2].zfill(2) if len(time_parts) > 2 else '00'
            
            normalized = f"{year}-{month}-{day} {hour}:{minute}:{second}"
            
            # 验证格式
            datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
            return normalized
        except Exception as e:
            print(f"警告: 无法解析时间戳 '{timestamp_str}': {e}")
            return None
    
    # 处理标准格式: 2025-11-01 20:54:02
    elif '-' in timestamp_str:
        try:
            # 如果没有秒，添加:00
            if len(timestamp_str.split(' ')) == 2:
                date_part, time_part = timestamp_str.split(' ')
                if len(time_part.split(':')) == 2:
                    timestamp_str = f"{date_part} {time_part}:00"
            
            # 验证格式
            datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return timestamp_str
        except Exception as e:
            print(f"警告: 无法解析时间戳 '{timestamp_str}': {e}")
            return None
    
    return None

def load_old_data():
    """
    加载old_data文件夹中的所有CSV文件并转换为新格式
    """
    all_data = []
    
    if not os.path.exists(OLD_DATA_DIR):
        print(f"错误: {OLD_DATA_DIR} 文件夹不存在")
        return pd.DataFrame()
    
    csv_files = [f for f in os.listdir(OLD_DATA_DIR) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"警告: {OLD_DATA_DIR} 文件夹中没有CSV文件")
        return pd.DataFrame()
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    for filename in csv_files:
        filepath = os.path.join(OLD_DATA_DIR, filename)
        print(f"\n处理文件: {filename}")
        
        # 提取mod_id
        mod_id = extract_mod_id_from_filename(filename)
        if mod_id is None:
            print(f"  警告: 无法从文件名 '{filename}' 提取mod_id，跳过")
            continue
        
        mod_name = MODS[mod_id]['name']
        print(f"  识别为: {mod_name} (ID: {mod_id})")
        
        try:
            # 读取CSV文件
            df = pd.read_csv(filepath)
            print(f"  读取了 {len(df)} 行数据")
            
            # 检查必需的列
            if 'current_subscribers' not in df.columns:
                print(f"  警告: 文件缺少 'current_subscribers' 列，跳过")
                continue
            
            if 'timestamp' not in df.columns:
                print(f"  警告: 文件缺少 'timestamp' 列，跳过")
                continue
            
            # 提取需要的列并重命名
            df_processed = df[['timestamp', 'current_subscribers']].copy()
            df_processed['mod_id'] = mod_id
            df_processed['subscribers'] = df_processed['current_subscribers']
            
            # 统一时间戳格式
            print(f"  统一时间戳格式...")
            df_processed['timestamp'] = df_processed['timestamp'].apply(normalize_timestamp)
            
            # 移除无法解析的时间戳
            before_count = len(df_processed)
            df_processed = df_processed.dropna(subset=['timestamp'])
            after_count = len(df_processed)
            if before_count != after_count:
                print(f"  移除了 {before_count - after_count} 行无效时间戳")
            
            # 选择需要的列
            df_processed = df_processed[['mod_id', 'timestamp', 'subscribers']]
            
            # 确保subscribers是整数
            df_processed['subscribers'] = df_processed['subscribers'].astype(int)
            
            all_data.append(df_processed)
            print(f"  成功处理 {len(df_processed)} 行数据")
            
        except Exception as e:
            print(f"  错误: 处理文件 '{filename}' 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # 合并所有数据
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\n总共合并了 {len(combined_df)} 行数据")
    
    return combined_df

def clean_data(df):
    """
    清理数据：去重、处理重复时间戳
    """
    if df.empty:
        return df
    
    print("\n清理数据...")
    original_count = len(df)
    
    # 按时间戳排序，确保"最新"的记录在后面
    df = df.sort_values(['mod_id', 'timestamp', 'subscribers'])
    
    # 对于同一(mod_id, timestamp)组合，保留subscribers值最大的记录
    # 如果subscribers相同，保留最后一条
    df = df.drop_duplicates(subset=['mod_id', 'timestamp'], keep='last')
    
    cleaned_count = len(df)
    removed_count = original_count - cleaned_count
    
    if removed_count > 0:
        print(f"  移除了 {removed_count} 行重复数据")
    
    # 按时间戳排序
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"  清理后剩余 {cleaned_count} 行数据")
    
    return df

def merge_with_existing(old_data_df):
    """
    合并旧数据到现有的mod_stats.csv
    """
    print("\n合并到现有数据...")
    
    # 读取现有数据
    if os.path.exists(CURRENT_DATA_FILE):
        existing_df = pd.read_csv(CURRENT_DATA_FILE)
        print(f"  读取了现有数据 {len(existing_df)} 行")
    else:
        existing_df = pd.DataFrame(columns=['mod_id', 'timestamp', 'subscribers'])
        print("  现有数据文件不存在，将创建新文件")
    
    # 合并数据
    combined_df = pd.concat([existing_df, old_data_df], ignore_index=True)
    print(f"  合并后共有 {len(combined_df)} 行数据")
    
    # 去重：基于(mod_id, timestamp)组合，保留最新的记录
    # 先按时间戳排序，然后去重
    combined_df = combined_df.sort_values(['mod_id', 'timestamp', 'subscribers'])
    combined_df = combined_df.drop_duplicates(subset=['mod_id', 'timestamp'], keep='last')
    
    # 最终排序
    combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
    
    final_count = len(combined_df)
    print(f"  去重后剩余 {final_count} 行数据")
    
    return combined_df

def validate_data(df):
    """
    验证合并后的数据
    """
    print("\n验证数据...")
    
    if df.empty:
        print("  警告: 数据为空")
        return False
    
    # 检查时间戳格式
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print("  [OK] 时间戳格式正确")
    except Exception as e:
        print(f"  [ERROR] 时间戳格式错误: {e}")
        return False
    
    # 检查重复的(mod_id, timestamp)组合
    duplicates = df.duplicated(subset=['mod_id', 'timestamp']).sum()
    if duplicates > 0:
        print(f"  [ERROR] 发现 {duplicates} 个重复的(mod_id, timestamp)组合")
        return False
    else:
        print("  [OK] 没有重复的(mod_id, timestamp)组合")
    
    # 检查数据范围
    min_time = df['timestamp'].min()
    max_time = df['timestamp'].max()
    print(f"  [OK] 数据时间范围: {min_time} 到 {max_time}")
    
    # 检查每个mod的数据量
    for mod_id in df['mod_id'].unique():
        mod_data = df[df['mod_id'] == mod_id]
        mod_name = MODS[mod_id]['name']
        print(f"  [OK] {mod_name}: {len(mod_data)} 条记录")
    
    return True

def main():
    """
    主函数
    """
    print("=" * 60)
    print("合并旧数据到 mod_stats.csv")
    print("=" * 60)
    
    # 备份现有数据
    if os.path.exists(CURRENT_DATA_FILE):
        import shutil
        shutil.copy2(CURRENT_DATA_FILE, BACKUP_FILE)
        print(f"\n已备份现有数据到: {BACKUP_FILE}")
    
    # 加载旧数据
    old_data_df = load_old_data()
    
    if old_data_df.empty:
        print("\n没有旧数据需要合并")
        return
    
    # 清理旧数据
    old_data_df = clean_data(old_data_df)
    
    # 记录合并前的现有数据行数
    if os.path.exists(CURRENT_DATA_FILE):
        existing_count = len(pd.read_csv(CURRENT_DATA_FILE))
    else:
        existing_count = 0
    
    # 合并到现有数据
    merged_df = merge_with_existing(old_data_df)
    
    # 验证数据
    if not validate_data(merged_df):
        print("\n数据验证失败，请检查错误信息")
        return
    
    # 保存合并后的数据
    merged_df.to_csv(CURRENT_DATA_FILE, index=False, encoding='utf-8-sig')
    print(f"\n[OK] 数据已保存到: {CURRENT_DATA_FILE}")
    
    # 生成统计报告
    print("\n" + "=" * 60)
    print("合并统计报告")
    print("=" * 60)
    print(f"现有数据行数: {existing_count}")
    print(f"旧数据行数: {len(old_data_df)}")
    print(f"合并后总行数: {len(merged_df)}")
    print(f"新增数据行数: {len(merged_df) - existing_count}")
    
    print("\n合并完成！")

if __name__ == "__main__":
    main()

