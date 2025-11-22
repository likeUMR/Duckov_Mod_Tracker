import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import schedule
from datetime import datetime
import os
import argparse
import pytz
from mod_config import MODS

# Configuration
DATA_FILE = 'mod_stats.csv'
PLOT_FILE = 'subscription_trends.png'
INTERVAL_MINUTES = 10

# Network configuration
# GitHub Actions runs on US Azure servers, usually no proxy needed for Steam
# If running locally in China, uncomment and modify the proxy port below
# PROXIES = {
#     'http': 'http://127.0.0.1:7890',
#     'https': 'http://127.0.0.1:7890',
# }
PROXIES = None

def get_beijing_time(rounded=False):
    """
    Get Beijing time string with second precision
    """
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_mod_data(mod_id, url):
    """
    获取单个Mod的订阅数据
    返回: (mod_id, subscribers) 或 None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        if '?' in url:
            req_url = url + '&l=english'
        else:
            req_url = url + '?l=english'

        session = requests.Session()
        retries = requests.adapters.HTTPAdapter(max_retries=3)
        session.mount('https://', retries)
        session.mount('http://', retries)

        response = session.get(req_url, headers=headers, timeout=30, proxies=PROXIES)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stats_table = soup.find('table', class_='stats_table')
        subscribers = 0
        
        if stats_table:
            rows = stats_table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    label = cols[1].text.strip()
                    if "Current Subscribers" in label:
                        count_text = cols[0].text.strip().replace(',', '')
                        subscribers = int(count_text)
                        break
        else:
            print(f"Warning: stats_table not found for mod_id {mod_id}")

        return (mod_id, subscribers)

    except requests.exceptions.Timeout:
        print(f"Timeout fetching mod_id {mod_id}. (If you are in China, please check your proxy settings)")
        return None
    except Exception as e:
        print(f"Error fetching mod_id {mod_id}: {e}")
        return None

def save_data(data_list, timestamp):
    """
    保存数据到CSV
    格式: mod_id, timestamp, subscribers
    """
    df_new = pd.DataFrame(data_list)
    df_new['timestamp'] = timestamp
    
    # Ensure correct column order: mod_id, timestamp, subscribers
    df_new = df_new[['mod_id', 'timestamp', 'subscribers']]
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def plot_trends():
    """
    读取CSV并绘制折线图
    复用公共绘图模块
    """
    from plot_utils import plot_trends_from_csv
    plot_trends_from_csv(DATA_FILE, PLOT_FILE)

def job():
    # Get current time rounded to minutes
    current_time = get_beijing_time()
    print(f"\n[{current_time}] Starting scraping job...")
    
    current_batch_data = []
    
    # First, fetch main mod to establish the reference timestamp
    from mod_config import MAIN_MOD_ID
    
    # Sort mods: main mod first, then others
    sorted_mods = sorted(MODS.items(), key=lambda x: (not x[1].get('is_main', False), x[0]))
    
    for mod_id, mod_info in sorted_mods:
        url = mod_info['url']
        name = mod_info['name']
        print(f"Fetching: {name} (ID: {mod_id})")
        
        result = get_mod_data(mod_id, url)
        if result:
            mod_id_fetched, subscribers = result
            print(f"  -> {name}: {subscribers} subscribers")
            current_batch_data.append({
                'mod_id': mod_id_fetched,
                'subscribers': subscribers
            })
        time.sleep(1)  # Polite delay

    if current_batch_data:
        save_data(current_batch_data, current_time)
        # Try to plot, but don't fail the job if plotting fails
        try:
            plot_trends()
        except Exception as e:
            print(f"Warning: Plotting failed: {e}")
            print("Continuing without plot update...")
    
    print("Job finished.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run the job once and exit (for CI/CD)')
    args = parser.parse_args()

    print("Mod Tracker started.")
    print(f"Tracking {len(MODS)} mods from mod_config.py")
    
    if args.once:
        print("Running in single-execution mode.")
        job()
    else:
        print(f"Interval: Every {INTERVAL_MINUTES} minutes")
        job() # 立即运行一次
        schedule.every(INTERVAL_MINUTES).minutes.do(job)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    main()
