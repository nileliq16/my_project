import json
import sys
from colorama import Fore, Style, init

# 初始化 colorama，讓顏色在不同作業系統上都能正常顯示
init(autoreset=True)

def show_subjects():
    """
    讀取 subjects.json 檔案，並根據學科狀態以不同顏色印出。
    """
    try:
        with open('subjects.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(Fore.RED + "錯誤：找不到 subjects.json 檔案。")
        print("請先建立 subjects.json 檔案，並填入您的學科盤點結果。")
        return
    except json.JSONDecodeError:
        print(Fore.RED + "錯誤：subjects.json 檔案格式不正確。")
        print("請檢查檔案內容是否為有效的 JSON 格式。")
        return

    print("--- 您的學科「紅黃綠」燈號盤點結果 ---\n")

    for subject in data.get('subjects', []):
        name = subject.get('name', '未知學科')
        status = subject.get('status', 'unknown').lower()
        description = subject.get('description', '沒有描述')

        if status == 'green':
            print(Fore.GREEN + f"✅ {name} (已精通)")
        elif status == 'yellow':
            print(Fore.YELLOW + f"🟡 {name} (半生不熟)")
        elif status == 'red':
            print(Fore.RED + f"🔴 {name} (完全陌生或困難)")
        else:
            print(Fore.WHITE + f"⚪️ {name} (狀態未知)")
        
        # 使用 Style.DIM 讓描述文字稍微變暗，更容易區分
        print(Style.DIM + f"   描述：{description}\n")

if __name__ == '__main__':
    # 檢查命令行參數
    if len(sys.argv) > 1 and sys.argv[1] == 'show-subjects':
        show_subjects()
    else:
        print("使用方式：python main.py show-subjects")