import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import matplotlib
matplotlib.use('Agg') # 设置非交互式后端，防止在无显示环境报错
import matplotlib.pyplot as plt
import schedule
from datetime import datetime
import os
import argparse
import pytz

# 配置
TRACK_FILE = 'track_target.txt'
DATA_FILE = 'mod_stats.csv'
PLOT_FILE = 'subscription_trends.png'
INTERVAL_MINUTES = 10

# 网络配置
# GitHub Actions 运行在美国Azure服务器，通常不需要代理访问Steam
# 如果你在本地国内运行，请取消下面代理的注释并修改端口
# PROXIES = {
#     'http': 'http://127.0.0.1:7890',
#     'https': 'http://127.0.0.1:7890',
# }
PROXIES = None

# 设置 matplotlib 中文字体
# 在 GitHub Actions Linux 环境下通常没有中文字体，需要回退到英文或安装字体
# 这里添加一些常见的 Linux/Mac/Windows 字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial', 'DejaVu Sans', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

def get_beijing_time():
    """获取北京时间字符串"""
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

def get_mod_data(url):
    """
    获取单个Mod的订阅数据
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
        
        title_div = soup.find('div', class_='workshopItemTitle')
        title = title_div.text.strip() if title_div else "Unknown Mod"
        
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
            print(f"Warning: stats_table not found for {url}")

        return {
            'url': url,
            'title': title,
            'subscribers': subscribers,
            'timestamp': get_beijing_time()
        }

    except requests.exceptions.Timeout:
        print(f"Timeout fetching {url}. (If you are in China, please check your proxy settings)")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def save_data(data_list):
    df_new = pd.DataFrame(data_list)
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def plot_trends():
    try:
        if not os.path.exists(DATA_FILE):
            print("No data file to plot.")
            return

        df = pd.read_csv(DATA_FILE)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        plt.figure(figsize=(12, 8))
        
        mods = df['url'].unique()
        total_subs = df.groupby('timestamp')['subscribers'].sum().reset_index()
        
        for mod_url in mods:
            mod_data = df[df['url'] == mod_url].sort_values('timestamp')
            if mod_data.empty: continue
            
            title = mod_data.iloc[-1]['title']
            plt.plot(mod_data['timestamp'], mod_data['subscribers'], label=title, marker='o', markersize=3)
            
            last_point = mod_data.iloc[-1]
            plt.text(last_point['timestamp'], last_point['subscribers'], f"{int(last_point['subscribers'])}", fontsize=9)

        if not total_subs.empty:
            plt.plot(total_subs['timestamp'], total_subs['subscribers'], label='Total (所有Mod总和)', 
                    linestyle='--', linewidth=2, color='black', marker='x')
            
            last_total = total_subs.iloc[-1]
            plt.text(last_total['timestamp'], last_total['subscribers'], f"Total: {int(last_total['subscribers'])}", 
                    fontsize=10, fontweight='bold')

        plt.title('Steam Mod Subscription Trends', fontsize=16) # 改为英文以避免乱码风险
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Subscribers', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(PLOT_FILE)
        print(f"Plot saved to {PLOT_FILE}")
        plt.close()

    except Exception as e:
        print(f"Error plotting: {e}")

def job():
    print(f"\n[{get_beijing_time()}] Starting scraping job...")
    
    if not os.path.exists(TRACK_FILE):
        print(f"Error: {TRACK_FILE} not found!")
        return

    with open(TRACK_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    current_batch_data = []
    
    for url in urls:
        print(f"Fetching: {url}")
        data = get_mod_data(url)
        if data:
            print(f"  -> {data['title']}: {data['subscribers']} subscribers")
            current_batch_data.append(data)
        time.sleep(1)

    if current_batch_data:
        save_data(current_batch_data)
        plot_trends()
    
    print("Job finished.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run the job once and exit (for CI/CD)')
    args = parser.parse_args()

    print("Mod Tracker started.")
    print(f"Tracking URLs from {TRACK_FILE}")
    
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
