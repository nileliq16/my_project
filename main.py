import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
import typer
from colorama import Fore, Style, init
from datetime import datetime

# 初始化 colorama
init(autoreset=True)

# --- 常數定義 ---
# 使用 Path 物件來處理檔案路徑，更具彈性
CWD = Path(__file__).parent
SUBJECTS_FILE = CWD / "subjects.json"
TASKS_FILE = CWD / "tasks.json"
RESOURCES_FILE = CWD / "resources.json"


# --- 輔助函式 (檔案處理) ---

def load_data(filepath: Path) -> Any:
    """載入 JSON 檔案並回傳其內容。若檔案不存在或格式錯誤，則回傳空列表。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # typer.secho 是 typer 內建的彩色 print，更方便
        typer.secho(f"警告：找不到檔案 {filepath}。將視為空檔案處理。", fg=typer.colors.YELLOW)
        return []
    except json.JSONDecodeError:
        typer.secho(f"錯誤：檔案 {filepath} 格式不正確。", fg=typer.colors.RED)
        sys.exit(1) # 發生嚴重錯誤時直接退出程式

def save_data(filepath: Path, data: Any):
    """將資料以美觀的 JSON 格式儲存至檔案。"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # indent=2 讓 JSON 格式化，方便閱讀
            # ensure_ascii=False 確保中文能正常顯示
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        typer.secho(f"錯誤：無法寫入檔案 {filepath}。錯誤訊息：{e}", fg=typer.colors.RED)
        sys.exit(1)


# --- Typer 應用程式實例化 ---

# 主應用程式
app = typer.Typer(help="學測致勝系統 CLI - 您的個人化學習引擎")
# 'task' 子命令群組
task_app = typer.Typer(help="管理您的學習任務")
# 將子命令群組加入主應用程式
app.add_typer(task_app, name="task")


# --- 核心邏輯函式 ---

def get_subjects_dict() -> Dict[int, Dict]:
    """讀取學科檔案，並轉換為以 ID 為鍵的字典以便快速查找。"""
    subjects_data = load_data(SUBJECTS_FILE)
    # 確保 subjects.json 的頂層是字典且包含 'subjects' 鍵
    if isinstance(subjects_data, dict) and 'subjects' in subjects_data:
        return {s['id']: s for s in subjects_data['subjects']}
    return {}

def show_subjects():
    """顯示所有學科的狀態"""
    subjects_dict = get_subjects_dict()
    if not subjects_dict:
        typer.secho("找不到任何學科資料，請檢查 subjects.json。", fg=typer.colors.RED)
        return

    print("--- 您的學科「紅黃綠」燈號盤點結果 ---\n")
    for subject in subjects_dict.values():
        name = subject.get('name', '未知學科')
        status = subject.get('status', 'unknown').lower()
        description = subject.get('description', '沒有描述')

        color_map = {
            'green': Fore.GREEN,
            'yellow': Fore.YELLOW,
            'red': Fore.RED
        }
        symbol_map = {
            'green': '✅',
            'yellow': '🟡',
            'red': '🔴'
        }
        
        color = color_map.get(status, Fore.WHITE)
        symbol = symbol_map.get(status, '⚪️')
        
        print(color + f"{symbol} {name} ({status.capitalize()})")
        print(Style.DIM + f"   描述：{description}\n")


# --- Typer 命令定義 ---

@app.command(name="show-subjects")
def show_subjects_command():
    """
    顯示所有學科的盤點狀態。
    """
    show_subjects()

@task_app.command(name="list")
def list_tasks(
    status: str = typer.Option("all", "--status", "-s", help="依狀態篩選任務 (all, todo, doing, done)")
):
    """
    列出所有任務。
    """
    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()

    if not tasks:
        typer.secho("目前沒有任何任務。", fg=typer.colors.YELLOW)
        return

    typer.secho(f"--- 任務列表 (狀態: {status}) ---", bold=True)
    
    status_colors = {
        "todo": typer.colors.RED,
        "doing": typer.colors.YELLOW,
        "done": typer.colors.GREEN,
    }

    found_task = False
    for task in tasks:
        task_status = task.get('status', 'unknown')
        if status.lower() != 'all' and task_status != status.lower():
            continue
        
        found_task = True
        subject_id = task.get('subject_id')
        subject_name = subjects_dict.get(subject_id, {}).get('name', '未知科目')
        
        color = status_colors.get(task_status, typer.colors.WHITE)
        
        typer.secho(f"ID: {task['task_id']:<3}", nl=False)
        typer.secho(f"[{task_status.upper():^5}] ", fg=color, nl=False)
        typer.secho(f"({subject_name}) ", fg=typer.colors.BLUE, nl=False)
        typer.secho(f"{task['description']}")

    if not found_task:
        typer.secho(f"找不到狀態為 '{status}' 的任務。", fg=typer.colors.YELLOW)


@task_app.command(name="add")
def add_task(
    description: str = typer.Argument(..., help="任務的詳細描述。"),
    subject_id: int = typer.Option(..., "--subject-id", "-id", prompt=True, help="此任務歸屬的學科ID。"),
    resource_code: Optional[str] = typer.Option(None, "--resource", "-r", help="關聯的資源代碼。"),
    due_date: Optional[str] = typer.Option(None, "--due", "-d", help="任務截止日期 (格式: YYYY-MM-DD)。")
):
    """
    新增一筆新的學習任務。
    """
    tasks = load_data(TASKS_FILE)

    # 自動計算新任務的 ID
    if not tasks:
        new_id = 1
    else:
        # 使用生成器表達式，更高效
        max_id = max(task.get('task_id', 0) for task in tasks)
        new_id = max_id + 1

    # 建立新任務的字典物件
    new_task = {
        "task_id": new_id,
        "subject_id": subject_id,
        "description": description,
        "resource_code": resource_code,
        "status": "todo", # 新任務預設為 'todo'
        "type": "study",   # 預設為 'study'
        "due_date": due_date,
        "peak_time_required": False, # 預設為 False
        "last_review_date": None,
        "next_review_date": None,
        "review_interval": 0
    }

    # 將新任務加入列表並儲存
    tasks.append(new_task)
    save_data(TASKS_FILE, tasks)

    typer.secho(f"✅ 成功新增任務 (ID: {new_id}): {description}", fg=typer.colors.GREEN)


if __name__ == '__main__':
    app()
