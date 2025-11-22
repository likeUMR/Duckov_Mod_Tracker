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

# 设置 matplotlib 字体
# 尝试加载本地字体以支持中文，如果不存在则使用默认
import matplotlib.font_manager as fm

FONT_PATH = 'SimHei.ttf' # 将尝试下载或使用此字体
my_font = None

def download_font():
    """下载中文字体以解决 GitHub Actions 乱码问题"""
    if not os.path.exists(FONT_PATH):
        print("Downloading SimHei font for Chinese support...")
        url = "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf"
        try:
            r = requests.get(url, stream=True)
            with open(FONT_PATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print("Font downloaded.")
        except Exception as e:
            print(f"Failed to download font: {e}")

# 尝试配置字体
try:
    # 检查并下载字体
    if not os.path.exists(FONT_PATH):
        # 在非本地环境(如GitHub Actions)尝试下载，或者你可以手动放一个字体文件在根目录
        # 为了演示简单，这里如果本地没有就不下载了，除非是明确需要
        # 但为了修复用户的乱码，我们这里做一个简单的检查
        # 注意：自动下载大文件可能影响速度，这里仅作为fallback
        pass

    if os.path.exists(FONT_PATH):
        my_font = fm.FontProperties(fname=FONT_PATH)
        plt.rcParams['font.sans-serif'] = [my_font.get_name()]
    else:
        # Fallback 列表
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial', 'DejaVu Sans']
except Exception as e:
    print(f"Font config error: {e}")

plt.rcParams['axes.unicode_minus'] = False

def get_beijing_time(rounded=False):
    """获取北京时间字符串"""
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    if rounded:
        # 归零秒数，确保同一批次时间完全一致
        now = now.replace(second=0, microsecond=0)
    return now.strftime('%Y-%m-%d %H:%M:%S')

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
            'subscribers': subscribers
            # timestamp removed from here, added in job()
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

        # 启用手绘风格 (xkcd style)
        with plt.xkcd():
            df = pd.read_csv(DATA_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            fig = plt.figure(figsize=(12, 8))
            
            mods = df['url'].unique()
            total_subs = df.groupby('timestamp')['subscribers'].sum().reset_index()
            
            # 获取所有时间点以便统一x轴
            all_times = df['timestamp'].unique()
            
            # 绘制每个Mod的曲线
            for mod_url in mods:
                mod_data = df[df['url'] == mod_url].sort_values('timestamp')
                if mod_data.empty: continue
                
                title = mod_data.iloc[-1]['title']
                plt.plot(mod_data['timestamp'], mod_data['subscribers'], label=title, marker='o', markersize=4)
                
                last_point = mod_data.iloc[-1]
                plt.text(last_point['timestamp'], last_point['subscribers'], f" {int(last_point['subscribers'])}", fontsize=9, ha='left', va='center')

            # 绘制总曲线
            if not total_subs.empty:
                plt.plot(total_subs['timestamp'], total_subs['subscribers'], label='Total', 
                        linestyle='--', linewidth=2, color='black', marker='x')
                
                last_total = total_subs.iloc[-1]
                plt.text(last_total['timestamp'], last_total['subscribers'], f" Total: {int(last_total['subscribers'])}", 
                        fontsize=10, fontweight='bold', ha='left', va='center')

            plt.title('Steam Mod Subscription Trends', fontsize=16)
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Subscribers', fontsize=12)
            
            # 优化X轴显示格式
            import matplotlib.dates as mdates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.gcf().autofmt_xdate() # 自动旋转日期标签
            
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.legend(loc='best')
            plt.tight_layout()
            
            plt.savefig(PLOT_FILE)
            print(f"Plot saved to {PLOT_FILE}")
            plt.close()

    except Exception as e:
        print(f"Error plotting: {e}")

def job():
    # 获取当前统一时间（归零秒数）
    current_time = get_beijing_time(rounded=True)
    print(f"\n[{current_time}] Starting scraping job...")
    
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
            # 统一注入时间戳
            data['timestamp'] = current_time
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
