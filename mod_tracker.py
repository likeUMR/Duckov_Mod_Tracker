import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import matplotlib.pyplot as plt
import schedule
from datetime import datetime
import os
import re

# 配置
TRACK_FILE = 'track_target.txt'
DATA_FILE = 'mod_stats.csv'
PLOT_FILE = 'subscription_trends.png'
INTERVAL_MINUTES = 10

# 网络配置
# 如果你在国内无法直接访问Steam，请取消下面代理的注释并根据你的代理端口修改 (例如 7890, 10809 等)
# PROXIES = {
#     'http': 'http://127.0.0.1:7890',
#     'https': 'http://127.0.0.1:7890',
# }
PROXIES = None  # 默认不使用代理

# 设置 matplotlib 中文字体 (尝试常见的Windows中文字体)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def get_mod_data(url):
    """
    获取单个Mod的订阅数据
    """
    try:
        # 强制使用英文以方便解析，防止语言自动切换导致解析失败
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        # 确保URL包含语言参数
        if '?' in url:
            req_url = url + '&l=english'
        else:
            req_url = url + '?l=english'

        # 使用 Session 和 Retry 增加稳定性
        session = requests.Session()
        retries = requests.adapters.HTTPAdapter(max_retries=3)
        session.mount('https://', retries)
        session.mount('http://', retries)

        response = session.get(req_url, headers=headers, timeout=30, proxies=PROXIES)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取标题
        title_div = soup.find('div', class_='workshopItemTitle')
        title = title_div.text.strip() if title_div else "Unknown Mod"
        
        # 获取订阅数
        # Steam创意工坊通常在一个表格结构中展示统计数据
        # 查找包含 "Current Subscribers" 的行
        stats_table = soup.find('table', class_='stats_table')
        subscribers = 0
        
        if stats_table:
            rows = stats_table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    label = cols[1].text.strip()
                    if "Current Subscribers" in label:
                        # 移除逗号并转换为整数
                        count_text = cols[0].text.strip().replace(',', '')
                        subscribers = int(count_text)
                        break
        else:
            # 备用方法：直接搜索文本（如果表格结构改变）
            # 有时候Steam可能会改变布局，或者对于拥有者/非拥有者显示不同
            print(f"Warning: stats_table not found for {url}")

        return {
            'url': url,
            'title': title,
            'subscribers': subscribers,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    except requests.exceptions.Timeout:
        print(f"Timeout fetching {url}. (If you are in China, please check your proxy settings)")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def save_data(data_list):
    """
    将数据追加保存到CSV
    """
    df_new = pd.DataFrame(data_list)
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def plot_trends():
    """
    读取CSV并绘制折线图
    """
    try:
        if not os.path.exists(DATA_FILE):
            print("No data file to plot.")
            return

        df = pd.read_csv(DATA_FILE)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        plt.figure(figsize=(12, 8))
        
        # 绘制每个Mod的曲线
        mods = df['url'].unique()
        
        # 准备总数数据
        total_subs = df.groupby('timestamp')['subscribers'].sum().reset_index()
        
        for mod_url in mods:
            mod_data = df[df['url'] == mod_url].sort_values('timestamp')
            # 获取该URL对应的最新标题（以防标题变更）
            title = mod_data.iloc[-1]['title']
            plt.plot(mod_data['timestamp'], mod_data['subscribers'], label=title, marker='o', markersize=3)
            
            # 在终点标注数值
            last_point = mod_data.iloc[-1]
            plt.text(last_point['timestamp'], last_point['subscribers'], f"{int(last_point['subscribers'])}", fontsize=9)

        # 绘制总曲线
        plt.plot(total_subs['timestamp'], total_subs['subscribers'], label='Total (所有Mod总和)', 
                 linestyle='--', linewidth=2, color='black', marker='x')
        
        # 标注总数终点
        last_total = total_subs.iloc[-1]
        plt.text(last_total['timestamp'], last_total['subscribers'], f"Total: {int(last_total['subscribers'])}", 
                 fontsize=10, fontweight='bold')

        plt.title('Steam Mod 订阅量变化趋势', fontsize=16)
        plt.xlabel('时间', fontsize=12)
        plt.ylabel('订阅数量', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(PLOT_FILE)
        print(f"Plot saved to {PLOT_FILE}")
        plt.close() # 关闭图形释放内存

    except Exception as e:
        print(f"Error plotting: {e}")

def job():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scraping job...")
    
    # 读取目标URL
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
        time.sleep(1) # 礼貌性延迟，避免请求过快

    if current_batch_data:
        save_data(current_batch_data)
        plot_trends()
    
    print("Job finished.")

def main():
    print("Mod Tracker started.")
    print(f"Tracking URLs from {TRACK_FILE}")
    print(f"Data will be saved to {DATA_FILE}")
    print(f"Plot will be saved to {PLOT_FILE}")
    print(f"Interval: Every {INTERVAL_MINUTES} minutes")
    
    # 立即运行一次
    job()
    
    # 设定定时任务
    schedule.every(INTERVAL_MINUTES).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

