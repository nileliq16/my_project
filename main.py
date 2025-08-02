import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
import typer
from colorama import Fore, Style, init
from datetime import datetime

# --- 核心模組 ---
from scheduler import update_review_schedule
from planner import get_daily_plan

# 初始化 colorama
init(autoreset=True)

# --- 常數定義 ---
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
        typer.secho(f"警告：找不到檔案 {filepath}。將視為空檔案處理。", fg=typer.colors.YELLOW)
        return []
    except json.JSONDecodeError:
        typer.secho(f"錯誤：檔案 {filepath} 格式不正確。", fg=typer.colors.RED)
        sys.exit(1)

def save_data(filepath: Path, data: Any):
    """將資料以美觀的 JSON 格式儲存至檔案。"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        typer.secho(f"錯誤：無法寫入檔案 {filepath}。錯誤訊息：{e}", fg=typer.colors.RED)
        sys.exit(1)


# --- Typer 應用程式實例化 ---

app = typer.Typer(help="學測致勝系統 CLI - 您的個人化學習引擎")
task_app = typer.Typer(help="管理您的學習任務")
app.add_typer(task_app, name="task")


# --- 核心邏輯函式 ---

def get_subjects_dict() -> Dict[str, Dict]:
    """讀取學科檔案，並轉換為以 ID 為鍵的字典以便快速查找。"""
    subjects_data = load_data(SUBJECTS_FILE)
    if isinstance(subjects_data, dict) and 'subjects' in subjects_data:
        return {s['id']: s for s in subjects_data['subjects']}
    return {}

# --- Typer 命令定義 ---

@app.command(name="plan")
def show_plan(
    daily: bool = typer.Option(False, "--daily", help="顯示每日學習計畫。")
):
    """
    根據您的任務排程，產生今日的學習計畫。
    """
    if not daily:
        typer.secho("請指定計畫類型，目前僅支援 --daily。", fg=typer.colors.YELLOW)
        raise typer.Exit()

    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()
    
    daily_plan = get_daily_plan(tasks)
    review_tasks = daily_plan.get('review_tasks', [])
    new_tasks = daily_plan.get('new_tasks', [])

    typer.secho(f"--- 📝 您的今日學習計畫 ({datetime.now().strftime('%Y-%m-%d')}) ---", bold=True, fg=typer.colors.BRIGHT_MAGENTA)

    # 顯示複習任務 (高優先級)
    typer.secho("\n🔥 高優先級複習 (逾期任務)", bold=True, fg=typer.colors.BRIGHT_RED)
    
    overdue_tasks = []
    due_today_tasks = []

    for task in review_tasks:
        try:
            next_review_date = datetime.strptime(task['next_review_date'], '%Y-%m-%d').date()
            overdue_days = (datetime.now().date() - next_review_date).days
            if overdue_days > 0:
                overdue_tasks.append((task, overdue_days))
            else:
                due_today_tasks.append(task)
        except (ValueError, TypeError):
            continue
    
    if not overdue_tasks:
        typer.secho("  沒有逾期項目，做得很好！", fg=typer.colors.GREEN)
    else:
        for task, days in sorted(overdue_tasks, key=lambda x: x[1], reverse=True):
            subject_id = task.get('subject_id')
            subject_name = subjects_dict.get(subject_id, {}).get('name', '未知科目')
            output = f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']}"
            typer.secho(f"{output} - ", nl=False, fg=typer.colors.RED)
            typer.secho(f"已逾期 {days} 天", bold=True, fg=typer.colors.RED)

    # 顯示今日到期複習任務
    typer.secho("\n💧 今日到期複習", bold=True, fg=typer.colors.BRIGHT_BLUE)
    if not due_today_tasks:
        typer.secho("  今日沒有到期的複習任務。", fg=typer.colors.GREEN)
    else:
        for task in sorted(due_today_tasks, key=lambda x: x.get('task_id')):
            subject_id = task.get('subject_id')
            subject_name = subjects_dict.get(subject_id, {}).get('name', '未知科目')
            output = f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']}"
            typer.secho(output, fg=typer.colors.BLUE)

    # 顯示新任務
    typer.secho("\n🚀 今日新任務", bold=True, fg=typer.colors.BRIGHT_GREEN)
    if not new_tasks:
        typer.secho("  沒有新的任務，記得去 'task add' 新增！")
    else:
        for task in new_tasks:
            subject_id = task.get('subject_id')
            subject_name = subjects_dict.get(subject_id, {}).get('name', '未知科目')
            typer.secho(f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']}", fg=typer.colors.GREEN)

    typer.secho("\n" + "="*50)
    typer.secho("💡 提示：使用 'python main.py task review <ID> -p <表現>' 來完成複習。", fg=typer.colors.CYAN)


@app.command(name="show-subjects")
def show_subjects_command():
    """顯示所有學科的盤點狀態。"""
    subjects_dict = get_subjects_dict()
    if not subjects_dict:
        typer.secho("找不到任何學科資料，請檢查 subjects.json。", fg=typer.colors.RED)
        return

    print("--- 您的學科「紅黃綠」燈號盤點結果 ---\n")
    for subject in subjects_dict.values():
        name = subject.get('name', '未知學科')
        status = subject.get('status', 'unknown').lower()
        description = subject.get('description', '沒有描述')

        color_map = {'green': Fore.GREEN, 'yellow': Fore.YELLOW, 'red': Fore.RED}
        symbol_map = {'green': '✅', 'yellow': '🟡', 'red': '🔴'}
        
        color = color_map.get(status, Fore.WHITE)
        symbol = symbol_map.get(status, '⚪️')
        
        print(color + f"{symbol} {name} ({status.capitalize()})")
        print(Style.DIM + f"   描述：{description}\n")

@task_app.command(name="list")
def list_tasks(
    status: str = typer.Option("all", "--status", "-s", help="依狀態篩選任務 (all, todo, doing, done)")
):
    """列出所有任務。"""
    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()

    if not tasks:
        typer.secho("目前沒有任何任務。", fg=typer.colors.YELLOW)
        return

    typer.secho(f"--- 任務列表 (狀態: {status}) ---", bold=True)
    
    status_colors = {"todo": typer.colors.RED, "doing": typer.colors.YELLOW, "done": typer.colors.GREEN}
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
        typer.secho(f"{task['description']}", nl=False)

        next_review = task.get('next_review_date')
        if next_review:
             typer.secho(f"  下次複習：{next_review}", fg=typer.colors.CYAN)
        else:
            typer.secho(f"  截止日期：{task.get('due_date', '未設定')}")

    if not found_task:
        typer.secho(f"找不到狀態為 '{status}' 的任務。", fg=typer.colors.YELLOW)

@task_app.command(name="add")
def add_task(
    description: str = typer.Argument(..., help="任務的詳細描述。"),
    subject_id: str = typer.Option(..., "--subject-id", "-id", prompt=True, help="此任務歸屬的學科ID。"),
    resource_code: Optional[str] = typer.Option(None, "--resource", "-r", help="關聯的資源代碼。"),
    due_date: Optional[str] = typer.Option(None, "--due", "-d", help="任務截止日期 (格式: YYYY-MM-DD)。")
):
    """新增一筆新的學習任務。"""
    tasks = load_data(TASKS_FILE)
    new_id = max((task.get('task_id', 0) for task in tasks), default=0) + 1

    new_task = {
        "task_id": new_id, "subject_id": subject_id, "description": description,
        "resource_code": resource_code, "status": "todo", "type": "study",
        "due_date": due_date, "peak_time_required": False,
        "last_review_date": None, "next_review_date": None, "review_interval": 0
    }
    tasks.append(new_task)
    save_data(TASKS_FILE, tasks)
    typer.secho(f"✅ 成功新增任務 (ID: {new_id}): {description}", fg=typer.colors.GREEN)

@task_app.command(name="review")
def review_task(
    task_id: int = typer.Argument(..., help="要複習的任務 ID。"),
    performance: str = typer.Option(
        ..., "--performance", "-p",
        prompt="你的複習表現如何？ (good, ok, bad)",
        help="你的複習表現 (good, ok, bad)"
    )
):
    """紀錄一次複習，並根據表現更新下一次複習排程。"""
    performance = performance.lower()
    if performance not in ['good', 'ok', 'bad']:
        typer.secho("錯誤：表現只能是 'good', 'ok', 或 'bad'。", fg=typer.colors.RED)
        raise typer.Exit()

    tasks = load_data(TASKS_FILE)
    task_to_update = None
    for task in tasks:
        if task.get('task_id') == task_id:
            task_to_update = task
            break

    if not task_to_update:
        typer.secho(f"錯誤：找不到 ID 為 {task_id} 的任務。", fg=typer.colors.RED)
        raise typer.Exit()

    updated_task = update_review_schedule(task_to_update, performance)
    save_data(TASKS_FILE, tasks)

    next_review_date = updated_task.get('next_review_date', 'N/A')
    typer.secho(f"✅ 任務 {task_id} 複習完畢！", fg=typer.colors.GREEN)
    typer.secho(f"   表現：{performance.capitalize()}")
    typer.secho(f"   下次複習日期已更新為：{next_review_date}", fg=typer.colors.CYAN)

if __name__ == '__main__':
    app()