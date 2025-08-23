# main.py (修正版)

import json
import sys
import sqlite3
import codecs # 引用 codecs 模組
from typing import List, Dict, Any, Optional
from pathlib import Path
import typer
from colorama import Fore, Style, init
from datetime import datetime, timezone
from collections import Counter

# --- 核心模組 ---
from scheduler import update_review_schedule
from planner import get_daily_plan

# 【修正點】: 強制將標準輸出/錯誤流的編碼設為 UTF-8
# 這可以解決在 Windows cmd 中輸出 Unicode 字元（如 Emoji）時的編碼錯誤問題
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 初始化 colorama，autoreset=True 確保每個 print 後樣式都會重設
init(autoreset=True)

# --- 常數定義 ---
CWD = Path(__file__).parent
SUBJECTS_FILE = CWD / "subjects.json"
TASKS_FILE = CWD / "tasks.json"
RESOURCES_FILE = CWD / "resources.json"
LOG_FILE = CWD / "log.json"
DB_FILE = CWD / "study_data.db"

# --- 樣式常數 ---
HEADER = Style.BRIGHT + Fore.MAGENTA
SUB_HEADER = Style.BRIGHT + Fore.CYAN
SUCCESS = Fore.GREEN
ERROR = Fore.RED
WARNING = Fore.YELLOW
INFO = Fore.CYAN
KEY = Fore.BLUE
DIM = Style.DIM


# --- 輔助函式 (檔案處理) ---

def load_data(filepath: Path) -> Any:
    """載入 JSON 檔案並回傳其內容。若檔案不存在或格式錯誤，則回傳空列表。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        if filepath != LOG_FILE:
            print(WARNING + f"警告：找不到檔案 {filepath}。將視為空檔案處理。")
        return []
    except json.JSONDecodeError:
        print(ERROR + f"錯誤：檔案 {filepath} 格式不正確。")
        sys.exit(1)

def save_data(filepath: Path, data: Any):
    """將資料以美觀的 JSON 格式儲存至檔案。"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(ERROR + f"錯誤：無法寫入檔案 {filepath}。錯誤訊息：{e}")
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

@app.command(name="export-sqlite")
def export_to_sqlite():
    """
    將 subjects.json 和 tasks.json 的資料匯出至 SQLite 資料庫。
    """
    print(HEADER + f"--- 正在將資料匯出至 {DB_FILE.name} ---")

    subjects_data = load_data(SUBJECTS_FILE)
    tasks_data = load_data(TASKS_FILE)

    if not isinstance(subjects_data, dict) or 'subjects' not in subjects_data:
        print(ERROR + "subjects.json 格式不正確或為空，無法匯出。")
        raise typer.Exit()
    
    subjects = subjects_data['subjects']

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            # --- 處理 Subjects 表 ---
            cursor.execute("DROP TABLE IF EXISTS subjects")
            cursor.execute("""
                CREATE TABLE subjects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT,
                    description TEXT
                )
            """)
            subject_rows = [(s['id'], s['name'], s['status'], s['description']) for s in subjects]
            cursor.executemany("INSERT INTO subjects VALUES (?, ?, ?, ?)", subject_rows)
            print(SUCCESS + f"  ✅ 成功寫入 {len(subject_rows)} 筆學科資料。")

            # --- 處理 Tasks 表 ---
            cursor.execute("DROP TABLE IF EXISTS tasks")
            cursor.execute("""
                CREATE TABLE tasks (
                    task_id INTEGER PRIMARY KEY,
                    subject_id TEXT,
                    description TEXT NOT NULL,
                    resource_code TEXT,
                    status TEXT,
                    type TEXT,
                    due_date TEXT,
                    peak_time_required INTEGER,
                    last_review_date TEXT,
                    next_review_date TEXT,
                    review_interval INTEGER,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id)
                )
            """)
            task_rows = [
                (
                    t['task_id'], t['subject_id'], t['description'], t.get('resource_code'),
                    t['status'], t['type'], t.get('due_date'), 
                    1 if t.get('peak_time_required') else 0,
                    t.get('last_review_date'), t.get('next_review_date'),
                    t.get('review_interval')
                ) for t in tasks_data
            ]
            cursor.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", task_rows)
            print(SUCCESS + f"  ✅ 成功寫入 {len(task_rows)} 筆任務資料。")
            
            conn.commit()

    except sqlite3.Error as e:
        print(ERROR + f"資料庫操作失敗：{e}")
        raise typer.Exit()

    print(Style.BRIGHT + SUCCESS + f"\n資料庫匯出成功！檔案已儲存於 {DB_FILE}")


@app.command(name="show-id")
def show_subject_ids():
    """列出所有學科的名稱及其對應的代碼 (ID)。"""
    subjects_dict = get_subjects_dict()
    if not subjects_dict:
        print(ERROR + "找不到任何學科資料，請檢查 subjects.json。")
        raise typer.Exit()
    
    print(HEADER + "--- 📖 學科代碼列表 ---")
    print(Style.BRIGHT + f"{'學科名稱':<6s} | {'學科代碼 (ID)'}")
    print(Style.BRIGHT + "-" * 25)
    
    for subject in subjects_dict.values():
        name = subject.get('name', '未知學科')
        subject_id = subject.get('id', 'N/A')
        print(f"{name:<7s}| " + INFO + f"{subject_id}")

@app.command(name="status")
def show_status():
    """快速檢查目前的整體學習狀態，顯示各科目的待辦任務數量。"""
    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()

    if not subjects_dict:
        print(ERROR + "找不到任何學科資料，請先設定 subjects.json。")
        raise typer.Exit()

    todo_counts = Counter(task['subject_id'] for task in tasks if task.get('status') == 'todo')
    print(HEADER + "--- 📊 學習狀態總覽 (各科待辦任務) ---")
    
    sorted_subjects = sorted(subjects_dict.values(), key=lambda s: todo_counts.get(s['id'], 0), reverse=True)

    for subject in sorted_subjects:
        subject_id, subject_name = subject.get('id'), subject.get('name', '未知科目')
        count = todo_counts.get(subject_id, 0)
        
        color = Fore.GREEN
        if count > 5: color = Fore.RED
        elif count > 2: color = Fore.YELLOW
            
        bar = "█" * count
        print(f"  - {subject_name:<6s}: " + Style.BRIGHT + color + f"{count:<2} 項 " + color + bar)
        
    total_todo = sum(todo_counts.values())
    print(DIM + "\n" + "-"*30)
    print(f"總計待辦任務: " + Style.BRIGHT + WARNING + f"{total_todo} 項")


@app.command(name="plan")
def show_plan(daily: bool = typer.Option(False, "--daily", help="顯示每日學習計畫。")):
    """根據您的任務排程，產生今日的學習計畫。"""
    if not daily:
        print(WARNING + "請指定計畫類型，目前僅支援 --daily。")
        raise typer.Exit()

    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()
    daily_plan = get_daily_plan(tasks)
    review_tasks, new_tasks = daily_plan.get('review_tasks', []), daily_plan.get('new_tasks', [])

    print(HEADER + f"--- 📝 您的今日學習計畫 ({datetime.now().strftime('%Y-%m-%d')}) ---")

    print(SUB_HEADER + "\n🔥 高優先級複習 (逾期任務)")
    overdue_tasks, due_today_tasks = [], []
    for task in review_tasks:
        try:
            next_review_date = datetime.strptime(task['next_review_date'], '%Y-%m-%d').date()
            overdue_days = (datetime.now().date() - next_review_date).days
            if overdue_days > 0: overdue_tasks.append((task, overdue_days))
            else: due_today_tasks.append(task)
        except (ValueError, TypeError): continue
    
    if not overdue_tasks: print(SUCCESS + "  沒有逾期項目，做得很好！")
    else:
        for task, days in sorted(overdue_tasks, key=lambda x: x[1], reverse=True):
            subject_name = subjects_dict.get(task.get('subject_id'), {}).get('name', '未知科目')
            print(ERROR + f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']} - " + Style.BRIGHT + f"已逾期 {days} 天")

    print(SUB_HEADER + "\n💧 今日到期複習")
    if not due_today_tasks: print(SUCCESS + "  今日沒有到期的複習任務。")
    else:
        for task in sorted(due_today_tasks, key=lambda x: x.get('task_id')):
            subject_name = subjects_dict.get(task.get('subject_id'), {}).get('name', '未知科目')
            print(Fore.BLUE + f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']}")

    print(SUB_HEADER + "\n🚀 今日新任務")
    if not new_tasks: print(SUCCESS + "  沒有新的任務，記得去 'task add' 新增！")
    else:
        for task in new_tasks:
            subject_name = subjects_dict.get(task.get('subject_id'), {}).get('name', '未知科目')
            print(Fore.GREEN + f"  - [ID: {task['task_id']:<2}] ({subject_name}) {task['description']}")

    print(DIM + "\n" + "="*50)
    print(INFO + "💡 提示：使用 'python main.py task complete <ID>' 來完成任務。")


@app.command(name="show-subjects")
def show_subjects_command():
    """顯示所有學科的盤點狀態。"""
    subjects_dict = get_subjects_dict()
    if not subjects_dict:
        print(ERROR + "找不到任何學科資料，請檢查 subjects.json。")
        return

    print(HEADER + "--- 您的學科「紅黃綠」燈號盤點結果 ---\n")
    for subject in subjects_dict.values():
        name, status, desc = subject.get('name', '未知學科'), subject.get('status', 'unknown').lower(), subject.get('description', '沒有描述')
        color_map = {'green': Fore.GREEN, 'yellow': Fore.YELLOW, 'red': Fore.RED}
        symbol_map = {'green': '✅', 'yellow': '🟡', 'red': '🔴'}
        color, symbol = color_map.get(status, Fore.WHITE), symbol_map.get(status, '⚪️')
        print(color + f"{symbol} {name} ({status.capitalize()})")
        print(DIM + f"   描述：{desc}\n")

@task_app.command(name="list")
def list_tasks(status: str = typer.Option("all", "--status", "-s", help="依狀態篩選任務 (all, todo, doing, done)")):
    """列出所有任務。"""
    tasks = load_data(TASKS_FILE)
    subjects_dict = get_subjects_dict()
    if not tasks:
        print(WARNING + "目前沒有任何任務。")
        return

    print(HEADER + f"--- 任務列表 (狀態: {status}) ---")
    status_colors = {"todo": Fore.RED, "doing": Fore.YELLOW, "done": Fore.GREEN}
    found_task = False
    for task in tasks:
        task_status = task.get('status', 'unknown')
        if status.lower() != 'all' and task_status != status.lower(): continue
        found_task = True
        subject_name = subjects_dict.get(task.get('subject_id'), {}).get('name', '未知科目')
        color = status_colors.get(task_status, Fore.WHITE)
        
        print(
            KEY + f"ID: {task['task_id']:<3} " +
            color + f"[{task_status.upper():^5}] " +
            Fore.BLUE + f"({subject_name}) " +
            Style.RESET_ALL + f"{task['description']}"
        )
        next_review = task.get('next_review_date')
        date_info = INFO + f"  下次複習：{next_review}" if next_review else DIM + f"  截止日期：{task.get('due_date', '未設定')}"
        print(date_info)

    if not found_task:
        print(WARNING + f"找不到狀態為 '{status}' 的任務。")

@task_app.command(name="add")
def add_task(
    description: str = typer.Argument(..., help="任務的詳細描述。"),
    subject_id: str = typer.Option(..., "--subject-id", "-id", help="此任務歸屬的學科ID。"),
    task_type: str = typer.Option("study", "--type", "-t", help="任務類型 (study, wellbeing)。"),
    resource_code: Optional[str] = typer.Option(None, "--resource", "-r", help="關聯的資源代碼。"),
    due_date: Optional[str] = typer.Option(None, "--due", "-d", help="任務截止日期 (格式: YYYY-MM-DD)。")
):
    """新增一筆新的學習任務。"""
    tasks = load_data(TASKS_FILE)
    new_id = max((task.get('task_id', 0) for task in tasks), default=0) + 1
    new_task = {
        "task_id": new_id, "subject_id": subject_id, "description": description, "resource_code": resource_code,
        "status": "todo", "type": task_type.lower(), "due_date": due_date, "peak_time_required": False,
        "last_review_date": None, "next_review_date": None, "review_interval": 0
    }
    tasks.append(new_task)
    save_data(TASKS_FILE, tasks)
    print(SUCCESS + f"✅ 成功新增任務 (ID: {new_id}): {description}")

@task_app.command(name="complete")
def complete_task(task_id: int = typer.Argument(..., help="要完成或複習的任務 ID。")):
    """完成一項任務或紀錄一次複習，並根據表現更新排程與寫入日誌。"""
    tasks = load_data(TASKS_FILE)
    task_to_update = next((task for task in tasks if task.get('task_id') == task_id), None)
    if not task_to_update:
        print(ERROR + f"錯誤：找不到 ID 為 {task_id} 的任務。")
        raise typer.Exit()

    print(HEADER + f"--- 正在完成任務 ID: {task_id} ({task_to_update['description']}) ---")
    performance = typer.prompt("你的複習/學習表現如何？ (good, ok, bad)").lower()
    while performance not in ['good', 'ok', 'bad']:
        print(WARNING + "無效的輸入，請重新輸入。")
        performance = typer.prompt("表現評分 (good, ok, bad)").lower()
    
    duration_minutes = typer.prompt("總共花了多少分鐘？", type=int)
    notes = typer.prompt("有什麼心得筆記嗎？ (可留空)", default="", show_default=False)

    activity_type = "review" if task_to_update.get('review_interval', 0) > 0 else "new_study"
    if activity_type == "new_study": task_to_update['status'] = 'done'

    log_data = load_data(LOG_FILE)
    if not isinstance(log_data, dict) or 'logs' not in log_data: log_data = {"logs": []}
    logs = log_data.get("logs", [])
    new_log_id = max((log.get('log_id', 0) for log in logs), default=0) + 1
    new_log = {
        "log_id": new_log_id, "task_id": task_id, "timestamp": datetime.now(timezone.utc).isoformat(),
        "activity_type": activity_type, "duration_minutes": duration_minutes, "performance": performance, "notes": notes
    }
    logs.append(new_log)
    save_data(LOG_FILE, {"logs": logs})
    print(SUCCESS + "學習活動已成功寫入日誌。")

    updated_task = update_review_schedule(task_to_update, performance)
    save_data(TASKS_FILE, tasks)
    next_review_date = updated_task.get('next_review_date', 'N/A')
    
    print(Style.BRIGHT + SUCCESS + f"✅ 任務 {task_id} 已完成！")
    print(INFO + f"   下次複習日期已更新為：{next_review_date}")

if __name__ == '__main__':
    app()