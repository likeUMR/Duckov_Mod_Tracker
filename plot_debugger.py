"""
调试脚本 - 用于本地测试绘图功能
复用公共绘图模块
"""
import os
from plot_utils import plot_trends_from_csv

# 配置
DATA_FILE = 'mod_stats.csv'
PLOT_FILE = 'subscription_trends_manual.png'

def plot_manual():
    """
    读取本地CSV并绘制折线图 (调试用)
    """
    plot_trends_from_csv(DATA_FILE, PLOT_FILE)

if __name__ == "__main__":
    plot_manual()
