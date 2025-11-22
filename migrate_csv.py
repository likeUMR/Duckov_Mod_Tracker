"""
将旧的 CSV 格式转换为新格式
旧格式: url, title, subscribers, timestamp
新格式: mod_id, timestamp, subscribers
"""
import pandas as pd
import re
from mod_config import MODS

OLD_DATA_FILE = 'mod_stats.csv'
NEW_DATA_FILE = 'mod_stats_new.csv'
BACKUP_FILE = 'mod_stats_backup.csv'

def extract_mod_id(url):
    """从 URL 中提取 mod_id"""
    match = re.search(r'id=(\d+)', url)
    if match:
        return int(match.group(1))
    return None

def migrate_csv():
    """迁移 CSV 格式"""
    try:
        # 读取旧格式
        df_old = pd.read_csv(OLD_DATA_FILE)
        
        # 创建备份
        df_old.to_csv(BACKUP_FILE, index=False, encoding='utf-8-sig')
        print(f"Backup saved to {BACKUP_FILE}")
        
        # 转换格式
        df_new = pd.DataFrame()
        df_new['mod_id'] = df_old['url'].apply(extract_mod_id)
        df_new['timestamp'] = df_old['timestamp']
        df_new['subscribers'] = df_old['subscribers']
        
        # 移除无效的 mod_id
        df_new = df_new.dropna(subset=['mod_id'])
        df_new['mod_id'] = df_new['mod_id'].astype(int)
        
        # 保存新格式
        df_new.to_csv(NEW_DATA_FILE, index=False, encoding='utf-8-sig')
        print(f"New format saved to {NEW_DATA_FILE}")
        print(f"Migrated {len(df_new)} records")
        
        # 询问是否替换原文件
        print(f"\nTo use the new format, rename {NEW_DATA_FILE} to {OLD_DATA_FILE}")
        
    except FileNotFoundError:
        print(f"{OLD_DATA_FILE} not found. Starting fresh with new format.")
    except Exception as e:
        print(f"Error migrating: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_csv()

