# 產生操作指南指示

## 角色

妳是一位台灣的教育專家、電腦科學家、軟體工程師，擅長領域包含輔導台灣高中生備考、開發備考系統。

## 任務

請妳根據先前建立的專案內容，整理出一份可以讓我測試所有命令的指引。

## 格式

整體指引請使用標準 Markdown 語法區塊呈現，命令部份也請使用方便我複製的區塊呈現。

## 要求

- 請使用**台灣繁體中文**回覆我。
- 我希望妳回覆我的時候，不要一段段落裡包含太多文字，盡量簡短俐落，但包含完整資訊。
- 我希望妳可以幫我標記重點。

## 對象

我是一位台灣的高中生，要準備考學測。

## 專案內容

### 主要專案程式碼

* main.py
```python
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
```

* planner.py

```python
# planner.py

from datetime import datetime
from typing import List, Dict, Any

def get_daily_plan(tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    從所有任務中掃描並產生今日的學習計畫。

    計畫包含：
    1. review_tasks: 所有今天到期或已逾期的複習任務。
    2. new_tasks: 所有從未被排入複習排程，且狀態為 'todo' 的新任務。

    Args:
        tasks: 完整的任務列表。

    Returns:
        一個字典，包含 'review_tasks' 和 'new_tasks' 兩個鍵，
        其值分別為對應的任務列表。
    """
    today = datetime.now().date()
    
    review_tasks = []
    new_tasks = []

    for task in tasks:
        is_review_task = False
        
        # --- 判斷是否為需要複習的任務 ---
        next_review_date_str = task.get('next_review_date')
        if next_review_date_str:
            try:
                # 將字串轉換為日期物件以進行比較
                next_review_date = datetime.strptime(next_review_date_str, '%Y-%m-%d').date()
                if next_review_date <= today:
                    review_tasks.append(task)
                    is_review_task = True
            except (ValueError, TypeError):
                # 若日期格式不正確或為 None，則忽略
                continue
        
        # 如果任務已經被歸類為複習任務，則不應再被視為新任務
        if is_review_task:
            continue

        # --- 判斷是否為尚未開始的新任務 ---
        # 條件：狀態為 'todo' 且從未被複習過 (即複習間隔為 0)
        is_brand_new_task = (
            task.get('status') == 'todo' and
            task.get('review_interval') == 0
        )
        if is_brand_new_task:
            new_tasks.append(task)
            
    return {
        "review_tasks": review_tasks,
        "new_tasks": new_tasks
    }
```

* reporter.py

```python
# reporter.py

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import defaultdict
import json
from pathlib import Path

# --- 定義檔案路徑 ---
CWD = Path(__file__).parent
LOG_FILE = CWD / "log.json"
TASKS_FILE = CWD / "tasks.json"
SUBJECTS_FILE = CWD / "subjects.json"

def _load_json_data(filepath: Path) -> List[Dict[str, Any]]:
    """一個輔助函式，用於載入 JSON 檔案中的列表資料。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                # 處理可能的 JSON 結構: {"logs": [...]} 或 {"subjects": [...]}
                key = next(iter(data))
                return data.get(key, [])
            return data
    except (FileNotFoundError, IndexError, json.JSONDecodeError, StopIteration):
        return []

def generate_weekly_report_ascii() -> str:
    """
    讀取日誌與任務檔案，產生一份 ASCII 格式的本週學習報告。
    報告包含各科學習時間長條圖，並標示出弱點科目。

    Returns:
        一個格式化後可用於終端機輸出的字串。
    """
    logs = _load_json_data(LOG_FILE)
    tasks = _load_json_data(TASKS_FILE)
    subjects = _load_json_data(SUBJECTS_FILE)

    if not logs or not tasks or not subjects:
        return "尚無足夠的資料可產生報告。"

    # 建立查找字典以提高效率
    task_to_subject_map = {task['task_id']: task['subject_id'] for task in tasks}
    subject_id_to_name_map = {s['id']: s.get('name', '未知科目') for s in subjects}

    # 計算本週數據
    today = datetime.now(timezone.utc).date()
    start_of_week = today - timedelta(days=today.weekday())
    
    time_distribution = defaultdict(float)
    bad_counts = defaultdict(int)

    for log in logs:
        try:
            log_timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            log_date = log_timestamp.date()

            if log_date >= start_of_week:
                task_id = log.get('task_id')
                subject_id = task_to_subject_map.get(task_id)
                if subject_id:
                    time_distribution[subject_id] += float(log.get('duration_minutes', 0))
                    if log.get('performance') == 'bad':
                        bad_counts[subject_id] += 1
        except (ValueError, TypeError, KeyError):
            continue

    if not time_distribution:
        return "本週尚無學習紀錄。"

    # 找出弱點科目
    weakest_subject_id = None
    if bad_counts:
        weakest_subject_id = max(bad_counts, key=bad_counts.get)

    # 準備繪製長條圖
    report_lines = []
    report_lines.append(f"--- 📊 本週學習時間分佈報告 (自 {start_of_week.strftime('%Y-%m-%d')} 起) ---")
    
    max_minutes = max(time_distribution.values()) if time_distribution else 1
    max_bar_width = 40  # 長條圖最大寬度

    # 根據學習時間排序
    sorted_subjects = sorted(time_distribution.items(), key=lambda item: item[1], reverse=True)

    for subject_id, total_minutes in sorted_subjects:
        subject_name = subject_id_to_name_map.get(subject_id, subject_id)
        hours = total_minutes / 60.0
        
        bar_width = int((total_minutes / max_minutes) * max_bar_width)
        bar = "█" * bar_width

        marker = "🔥" if subject_id == weakest_subject_id else ""
        
        line = f"{subject_name:<6s} | {hours:4.1f} hrs | {bar} {marker}"
        report_lines.append(line)
        
    if weakest_subject_id:
        weakest_subject_name = subject_id_to_name_map.get(weakest_subject_id, weakest_subject_id)
        report_lines.append("\n" + "="*50)
        report_lines.append(f"🔥 弱點提醒：本週「{weakest_subject_name}」的 'bad' 評等次數最多，請多加注意！")

    return "\n".join(report_lines)
```

* scheduler.py

```python
# scheduler.py

from datetime import datetime, timedelta
from typing import Dict, Any

# 定義萊特納系統的複習間隔（天）。每個數字代表一個「盒子」。
# 盒子 1: 1 天後複習
# 盒子 2: 3 天後複習
# ...以此類推
LEITNER_INTERVALS = [1, 3, 7, 14, 30]

def update_review_schedule(task: Dict[str, Any], performance: str) -> Dict[str, Any]:
    """
    根據表現使用萊特納系統更新任務的複習排程。

    - "good" 或 "ok" 的表現會將任務移至下一個複習盒子。
    - "bad" 的表現會將任務重設回第一個複習盒子。

    Args:
        task: 要更新的任務字典。
        performance: 複習表現，可為 "good", "ok", 或 "bad"。

    Returns:
        更新後的任務字典。
    """
    today = datetime.now().date()
    task['last_review_date'] = today.isoformat()

    current_interval = task.get('review_interval', 0)

    new_interval = current_interval

    if performance in ['good', 'ok']:
        # 表現良好或尚可 -> 移至下一個盒子
        if current_interval == 0:
            # 如果是第一次複習，移至第一個盒子
            new_interval = LEITNER_INTERVALS[0]
        else:
            try:
                # 找到目前間隔在序列中的位置，並推進到下一個
                current_index = LEITNER_INTERVALS.index(current_interval)
                next_index = current_index + 1
                if next_index < len(LEITNER_INTERVALS):
                    new_interval = LEITNER_INTERVALS[next_index]
                else:
                    # 已完成所有預設的盒子，維持在最長的間隔
                    new_interval = LEITNER_INTERVALS[-1]
            except ValueError:
                # 如果當前的間隔不在預設序列中，將其重設回第一個盒子
                new_interval = LEITNER_INTERVALS[0]

    elif performance == 'bad':
        # 表現不佳 -> 無論如何都重設回第一個盒子
        new_interval = LEITNER_INTERVALS[0]

    # 更新任務的間隔和下一次複習日期
    task['review_interval'] = new_interval
    if new_interval > 0:
        next_review_date = today + timedelta(days=new_interval)
        task['next_review_date'] = next_review_date.isoformat()
    else:
        # 如果間隔為 0，表示沒有排定的複習
        task['next_review_date'] = None

    return task
```

### 配合使用資料檔案

* subjects.json

```json
{
  "subjects": [
    {
      "id":"math",
      "name": "數學",
      "status": "red",
      "description": "微積分部分的概念還有些模糊，特別是應用題的部分。"
    },
    {
      "id":"phy",
      "name": "物理",
      "status": "red",
      "description": "電磁學完全無法理解，需要從頭開始學習。"
    },
    {
      "id":"chem",
      "name": "化學",
      "status": "red",
      "description": "對於化學鍵節的部分不熟悉。"
    },
    {
      "id":"bio",
      "name": "生物",
      "status": "red",
      "description": "激素調節的部分還有些模糊。"
    },
    {
      "id":"earth",
      "name": "地科",
      "status": "red",
      "description": "大氣層的部分不清楚。"
    },
    {
      "id":"eng",
      "name": "英文",
      "status": "red",
      "description": "單字量不夠，需要加強背誦。"
    },
    {
      "id":"chi",
      "name": "國文",
      "status": "red",
      "description": "文言文閱讀解讀困難。"
    },
    {
      "id":"health",
      "name": "健康",
      "status": "red",
      "description": "身體狀態不佳。"
    }
  ]
}
```

* tasks.json

```json
[
  {
    "task_id": 1,
    "subject_id": "math",
    "description": "壓力測試任務_001",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 2,
    "subject_id": "chem",
    "description": "壓力測試任務_002",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 3,
    "subject_id": "earth",
    "description": "壓力測試任務_003",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 4,
    "subject_id": "health",
    "description": "壓力測試任務_004",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 5,
    "subject_id": "phy",
    "description": "壓力測試任務_005",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 6,
    "subject_id": "chi",
    "description": "壓力測試任務_006",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 7,
    "subject_id": "eng",
    "description": "壓力測試任務_007",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 8,
    "subject_id": "eng",
    "description": "壓力測試任務_008",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 9,
    "subject_id": "bio",
    "description": "壓力測試任務_009",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 10,
    "subject_id": "eng",
    "description": "壓力測試任務_010",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 11,
    "subject_id": "bio",
    "description": "壓力測試任務_011",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 12,
    "subject_id": "phy",
    "description": "壓力測試任務_012",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 13,
    "subject_id": "chem",
    "description": "壓力測試任務_013",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 14,
    "subject_id": "eng",
    "description": "壓力測試任務_014",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 15,
    "subject_id": "bio",
    "description": "壓力測試任務_015",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 16,
    "subject_id": "phy",
    "description": "壓力測試任務_016",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 17,
    "subject_id": "chem",
    "description": "壓力測試任務_017",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 18,
    "subject_id": "eng",
    "description": "壓力測試任務_018",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 19,
    "subject_id": "earth",
    "description": "壓力測試任務_019",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 20,
    "subject_id": "math",
    "description": "壓力測試任務_020",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 21,
    "subject_id": "earth",
    "description": "壓力測試任務_021",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 22,
    "subject_id": "math",
    "description": "壓力測試任務_022",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 23,
    "subject_id": "math",
    "description": "壓力測試任務_023",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 24,
    "subject_id": "eng",
    "description": "壓力測試任務_024",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 25,
    "subject_id": "bio",
    "description": "壓力測試任務_025",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 26,
    "subject_id": "chi",
    "description": "壓力測試任務_026",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 27,
    "subject_id": "earth",
    "description": "壓力測試任務_027",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 28,
    "subject_id": "earth",
    "description": "壓力測試任務_028",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 29,
    "subject_id": "phy",
    "description": "壓力測試任務_029",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 30,
    "subject_id": "earth",
    "description": "壓力測試任務_030",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 31,
    "subject_id": "health",
    "description": "壓力測試任務_031",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 32,
    "subject_id": "chi",
    "description": "壓力測試任務_032",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 33,
    "subject_id": "health",
    "description": "壓力測試任務_033",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 34,
    "subject_id": "earth",
    "description": "壓力測試任務_034",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 35,
    "subject_id": "eng",
    "description": "壓力測試任務_035",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 36,
    "subject_id": "chem",
    "description": "壓力測試任務_036",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 37,
    "subject_id": "bio",
    "description": "壓力測試任務_037",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 38,
    "subject_id": "eng",
    "description": "壓力測試任務_038",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 39,
    "subject_id": "phy",
    "description": "壓力測試任務_039",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 40,
    "subject_id": "chem",
    "description": "壓力測試任務_040",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 41,
    "subject_id": "phy",
    "description": "壓力測試任務_041",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 42,
    "subject_id": "math",
    "description": "壓力測試任務_042",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 43,
    "subject_id": "bio",
    "description": "壓力測試任務_043",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 44,
    "subject_id": "earth",
    "description": "壓力測試任務_044",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 45,
    "subject_id": "math",
    "description": "壓力測試任務_045",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 46,
    "subject_id": "math",
    "description": "壓力測試任務_046",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 47,
    "subject_id": "chi",
    "description": "壓力測試任務_047",
    "resource_code": null,
    "status": "todo",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": null,
    "next_review_date": null,
    "review_interval": 0
  },
  {
    "task_id": 48,
    "subject_id": "phy",
    "description": "壓力測試任務_048",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 49,
    "subject_id": "earth",
    "description": "壓力測試任務_049",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  },
  {
    "task_id": 50,
    "subject_id": "chem",
    "description": "壓力測試任務_050",
    "resource_code": null,
    "status": "done",
    "type": "study",
    "due_date": null,
    "peak_time_required": false,
    "last_review_date": "2025-08-23",
    "next_review_date": "2025-08-24",
    "review_interval": 1
  }
]
```

* resources.json

```json
[
  {
    "resource_code": "math_ref_book_1",
    "name": "數學大滿貫A 1-2",
    "type": "參考書",
    "subject_id": "math"
  },
  {
    "resource_code": "eng_vocab_7000",
    "name": "7000單字",
    "type": "單字書",
    "subject_id": "eng"
  },
  {
    "resource_code": "chem_ref_book",
    "name": "好好學化學學測總複習講義",
    "type": "參考書",
    "subject_id": "chem"
  },
  {
    "resource_code": "bio_ref_book",
    "name": "高中學測週計畫-生物",
    "type": "參考書",
    "subject_id": "bio"
  },
  {
    "resource_code": "chi_ref_book",
    "name": "國文大模神",
    "type": "參考書",
    "subject_id": "chi"
  },
  {
    "resource_code": "earth_ref_book",
    "name": "好好學地科學測總複習講義",
    "type": "參考書",
    "subject_id": "earth"
  },
  {
    "resource_code": "phy_ref_book",
    "name": "物理新大滿貫",
    "type": "參考書",
    "subject_id": "phy"
  }

]
```

* log.json

```json

{
  "logs": [
    {
      "log_id": 1,
      "task_id": 39,
      "timestamp": "2025-08-23T12:19:49.805452+00:00",
      "activity_type": "new_study",
      "duration_minutes": 80,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 39."
    },
    {
      "log_id": 2,
      "task_id": 19,
      "timestamp": "2025-08-23T12:19:50.107410+00:00",
      "activity_type": "new_study",
      "duration_minutes": 86,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 19."
    },
    {
      "log_id": 3,
      "task_id": 20,
      "timestamp": "2025-08-23T12:19:50.403676+00:00",
      "activity_type": "new_study",
      "duration_minutes": 85,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 20."
    },
    {
      "log_id": 4,
      "task_id": 17,
      "timestamp": "2025-08-23T12:19:50.709298+00:00",
      "activity_type": "new_study",
      "duration_minutes": 37,
      "performance": "good",
      "notes": "自動化測試筆記 for task 17."
    },
    {
      "log_id": 5,
      "task_id": 23,
      "timestamp": "2025-08-23T12:19:51.015066+00:00",
      "activity_type": "new_study",
      "duration_minutes": 58,
      "performance": "good",
      "notes": "自動化測試筆記 for task 23."
    },
    {
      "log_id": 6,
      "task_id": 49,
      "timestamp": "2025-08-23T12:19:51.320913+00:00",
      "activity_type": "new_study",
      "duration_minutes": 81,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 49."
    },
    {
      "log_id": 7,
      "task_id": 12,
      "timestamp": "2025-08-23T12:19:51.631974+00:00",
      "activity_type": "new_study",
      "duration_minutes": 87,
      "performance": "good",
      "notes": "自動化測試筆記 for task 12."
    },
    {
      "log_id": 8,
      "task_id": 21,
      "timestamp": "2025-08-23T12:19:51.926904+00:00",
      "activity_type": "new_study",
      "duration_minutes": 74,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 21."
    },
    {
      "log_id": 9,
      "task_id": 22,
      "timestamp": "2025-08-23T12:19:52.232255+00:00",
      "activity_type": "new_study",
      "duration_minutes": 84,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 22."
    },
    {
      "log_id": 10,
      "task_id": 35,
      "timestamp": "2025-08-23T12:19:52.530515+00:00",
      "activity_type": "new_study",
      "duration_minutes": 87,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 35."
    },
    {
      "log_id": 11,
      "task_id": 25,
      "timestamp": "2025-08-23T12:19:52.833013+00:00",
      "activity_type": "new_study",
      "duration_minutes": 45,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 25."
    },
    {
      "log_id": 12,
      "task_id": 45,
      "timestamp": "2025-08-23T12:19:53.137973+00:00",
      "activity_type": "new_study",
      "duration_minutes": 76,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 45."
    },
    {
      "log_id": 13,
      "task_id": 10,
      "timestamp": "2025-08-23T12:19:53.442638+00:00",
      "activity_type": "new_study",
      "duration_minutes": 44,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 10."
    },
    {
      "log_id": 14,
      "task_id": 42,
      "timestamp": "2025-08-23T12:19:53.746590+00:00",
      "activity_type": "new_study",
      "duration_minutes": 12,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 42."
    },
    {
      "log_id": 15,
      "task_id": 36,
      "timestamp": "2025-08-23T12:19:54.049235+00:00",
      "activity_type": "new_study",
      "duration_minutes": 25,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 36."
    },
    {
      "log_id": 16,
      "task_id": 29,
      "timestamp": "2025-08-23T12:19:54.363280+00:00",
      "activity_type": "new_study",
      "duration_minutes": 45,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 29."
    },
    {
      "log_id": 17,
      "task_id": 31,
      "timestamp": "2025-08-23T12:19:54.661759+00:00",
      "activity_type": "new_study",
      "duration_minutes": 58,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 31."
    },
    {
      "log_id": 18,
      "task_id": 50,
      "timestamp": "2025-08-23T12:19:54.968259+00:00",
      "activity_type": "new_study",
      "duration_minutes": 71,
      "performance": "good",
      "notes": "自動化測試筆記 for task 50."
    },
    {
      "log_id": 19,
      "task_id": 34,
      "timestamp": "2025-08-23T12:19:55.271858+00:00",
      "activity_type": "new_study",
      "duration_minutes": 82,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 34."
    },
    {
      "log_id": 20,
      "task_id": 16,
      "timestamp": "2025-08-23T12:19:55.568869+00:00",
      "activity_type": "new_study",
      "duration_minutes": 28,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 16."
    },
    {
      "log_id": 21,
      "task_id": 48,
      "timestamp": "2025-08-23T12:19:55.884182+00:00",
      "activity_type": "new_study",
      "duration_minutes": 34,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 48."
    },
    {
      "log_id": 22,
      "task_id": 5,
      "timestamp": "2025-08-23T12:19:56.185200+00:00",
      "activity_type": "new_study",
      "duration_minutes": 78,
      "performance": "good",
      "notes": "自動化測試筆記 for task 5."
    },
    {
      "log_id": 23,
      "task_id": 30,
      "timestamp": "2025-08-23T12:19:56.484892+00:00",
      "activity_type": "new_study",
      "duration_minutes": 74,
      "performance": "good",
      "notes": "自動化測試筆記 for task 30."
    },
    {
      "log_id": 24,
      "task_id": 41,
      "timestamp": "2025-08-23T12:19:56.779502+00:00",
      "activity_type": "new_study",
      "duration_minutes": 17,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 41."
    },
    {
      "log_id": 25,
      "task_id": 18,
      "timestamp": "2025-08-23T12:19:57.076216+00:00",
      "activity_type": "new_study",
      "duration_minutes": 68,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 18."
    },
    {
      "log_id": 26,
      "task_id": 28,
      "timestamp": "2025-08-23T12:19:57.387666+00:00",
      "activity_type": "new_study",
      "duration_minutes": 82,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 28."
    },
    {
      "log_id": 27,
      "task_id": 13,
      "timestamp": "2025-08-23T12:19:57.696007+00:00",
      "activity_type": "new_study",
      "duration_minutes": 62,
      "performance": "ok",
      "notes": "自動化測試筆記 for task 13."
    },
    {
      "log_id": 28,
      "task_id": 26,
      "timestamp": "2025-08-23T12:19:58.000836+00:00",
      "activity_type": "new_study",
      "duration_minutes": 27,
      "performance": "good",
      "notes": "自動化測試筆記 for task 26."
    },
    {
      "log_id": 29,
      "task_id": 38,
      "timestamp": "2025-08-23T12:19:58.325799+00:00",
      "activity_type": "new_study",
      "duration_minutes": 46,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 38."
    },
    {
      "log_id": 30,
      "task_id": 46,
      "timestamp": "2025-08-23T12:19:58.627058+00:00",
      "activity_type": "new_study",
      "duration_minutes": 88,
      "performance": "bad",
      "notes": "自動化測試筆記 for task 46."
    }
  ]
}
```

### 壓力測試程式碼

* stress_test.py

```python
# stress_test.py (最終修正版)

import typer
import subprocess
import json
import random
import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

# --- 常數定義 ---
CWD = Path(__file__).parent
MAIN_SCRIPT = CWD / "main.py"
TASKS_FILE = CWD / "tasks.json"
LOG_FILE = CWD / "log.json"
SUBJECTS_FILE = CWD / "subjects.json"

# --- 樣式常數 ---
HEADER = Style.BRIGHT + Fore.MAGENTA
SUCCESS = Style.BRIGHT + Fore.GREEN
ERROR = Style.BRIGHT + Fore.RED
WARNING = Style.BRIGHT + Fore.YELLOW
INFO = Style.BRIGHT + Fore.CYAN
DIM = Style.DIM

def run_command(command: list, input_text: str = None) -> subprocess.CompletedProcess:
    """執行一個 CLI 命令，並設定好處理中文編碼的環境。"""
    try:
        child_env = {**os.environ, "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, str(MAIN_SCRIPT)] + command,
            input=input_text,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=child_env
        )
        if result.returncode != 0:
            # 如果 main.py 真的出錯，就印出錯誤訊息
            print(ERROR + f"\n命令 '{' '.join(command)}' 執行失敗 (Return Code: {result.returncode}):")
            print(DIM + "--- STDOUT ---")
            print(DIM + (result.stdout or "No stdout captured."))
            print(ERROR + "--- STDERR ---")
            print(ERROR + (result.stderr or "No stderr captured."))
        return result
    except FileNotFoundError:
        print(ERROR + f"錯誤：找不到主程式 'main.py'。")
        raise

def cleanup_data_files():
    """重設 tasks.json 和 log.json 以進行乾淨的測試。"""
    print(INFO + "--- 正在清理舊的測試資料 ---")
    TASKS_FILE.write_text("[]", encoding='utf-8')
    LOG_FILE.write_text('{"logs": []}', encoding='utf-8')
    print(SUCCESS + "  ✅ 資料檔案已重設。")

def get_valid_subject_ids() -> list:
    """從 subjects.json 讀取有效的學科 ID。"""
    try:
        with open(SUBJECTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ids = [s['id'] for s in data.get('subjects', [])]
        if not ids:
            print(ERROR + "subjects.json 中找不到任何學科 ID，測試無法繼續。")
            raise typer.Exit()
        return ids
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(ERROR + f"讀取 subjects.json 失敗: {e}")
        raise typer.Exit()

def main(
    tasks_to_add: int = typer.Option(50, help="要快速新增的任務數量。"),
    tasks_to_complete: int = typer.Option(30, help="要從新增的任務中隨機完成的數量。")
):
    """
    對學習系統執行壓力測試：大量新增、完成任務，並驗證結果。
    """
    if tasks_to_complete > tasks_to_add:
        print(ERROR + "要完成的任務數量不能大於新增的數量。")
        raise typer.Exit()

    cleanup_data_files()
    valid_ids = get_valid_subject_ids()
    
    # --- 階段一：大量新增任務 ---
    print(HEADER + f"\n--- 階段一：壓力測試 - 新增 {tasks_to_add} 個任務 ---")
    add_success_count = 0
    for i in range(1, tasks_to_add + 1):
        subject_id = random.choice(valid_ids)
        desc = f"壓力測試任務_{i:03d}"
        print(f"  - 新增任務 {i}/{tasks_to_add} (科目: {subject_id})... ", end="")
        result = run_command(["task", "add", desc, "--subject-id", subject_id])
        if result.returncode == 0 and "成功新增任務" in result.stdout:
            add_success_count += 1
            print(SUCCESS + "成功")
        else:
            print(ERROR + "失敗")
    print(SUCCESS + f"  ✅ 完成！成功新增 {add_success_count}/{tasks_to_add} 個任務。")

    # --- 階段二：大量完成任務 ---
    print(HEADER + f"\n--- 階段二：壓力測試 - 完成 {tasks_to_complete} 個任務 ---")
    task_ids_to_complete = random.sample(range(1, tasks_to_add + 1), tasks_to_complete)
    complete_success_count = 0
    performances = ["good", "ok", "bad"]
    for i, task_id in enumerate(task_ids_to_complete, 1):
        performance = random.choice(performances)
        duration = random.randint(10, 90)
        notes = f"自動化測試筆記 for task {task_id}."
        print(f"  - 完成任務 {i}/{tasks_to_complete} (ID: {task_id}, 表現: {performance})... ", end="")
        
        user_input = f"{performance}\n{duration}\n{notes}\n"
        
        # 【修正點】: 改變驗證邏輯
        # 1. 執行命令前，先記錄目前的日誌數量
        try:
            log_before = len(json.loads(LOG_FILE.read_text(encoding='utf-8'))['logs'])
        except (FileNotFoundError, json.JSONDecodeError):
            log_before = 0
            
        # 2. 執行命令
        result = run_command(["task", "complete", str(task_id)], input_text=user_input)

        # 3. 執行命令後，再次檢查日誌數量
        try:
            log_after = len(json.loads(LOG_FILE.read_text(encoding='utf-8'))['logs'])
        except (FileNotFoundError, json.JSONDecodeError):
            log_after = log_before

        # 4. 如果命令成功執行且日誌數量增加，才算成功
        if result.returncode == 0 and log_after == log_before + 1:
            complete_success_count += 1
            print(SUCCESS + "成功")
        else:
            print(ERROR + "失敗")

    print(SUCCESS + f"  ✅ 完成！成功回報 {complete_success_count}/{tasks_to_complete} 個任務。")

    # --- 階段三：生成報告與驗證 ---
    print(HEADER + "\n--- 階段三：驗證與報告 ---")
    # ... (後續報告部分不變) ...
    final_tasks = json.loads(TASKS_FILE.read_text(encoding='utf-8'))
    final_logs = json.loads(LOG_FILE.read_text(encoding='utf-8'))
    
    print(INFO + "1. 驗證 JSON 檔案完整性...")
    tasks_ok = len(final_tasks) == tasks_to_add
    logs_ok = len(final_logs['logs']) == tasks_to_complete
    print(f"  - tasks.json 應有 {tasks_to_add} 筆任務 -> " + (SUCCESS + f"實際找到 {len(final_tasks)} 筆" if tasks_ok else ERROR + f"實際找到 {len(final_tasks)} 筆"))
    print(f"  - log.json 應有 {tasks_to_complete} 筆紀錄 -> " + (SUCCESS + f"實際找到 {len(final_logs['logs'])} 筆" if logs_ok else ERROR + f"實際找到 {len(final_logs['logs'])} 筆"))

    print(INFO + "2. 抽樣驗證任務排程...")
    completed_tasks_logic_ok = True
    if not task_ids_to_complete:
        print(WARNING + "  - 沒有完成任何任務，跳過排程驗證。")
    else:
        for task_id in task_ids_to_complete[:3]:
            task = next((t for t in final_tasks if t['task_id'] == task_id), None)
            if task and not (task['status'] == 'done' and \
                    task['last_review_date'] == str(date.today()) and \
                    datetime.strptime(task['next_review_date'], '%Y-%m-%d').date() > date.today() and \
                    task['review_interval'] > 0):
                completed_tasks_logic_ok = False
                print(ERROR + f"  - ID {task_id} 的排程邏輯異常。")
        if completed_tasks_logic_ok:
            print(SUCCESS + "  - 已完成任務的排程邏輯（抽樣）看起來正確。")

    print(INFO + "3. 執行內建報告指令...")
    print(DIM + "\n--- `status` 指令輸出 ---")
    status_result = run_command(["status"])
    print(status_result.stdout.strip())
    print(DIM + "------------------------")

    print(DIM + "\n--- `plan --daily` 指令輸出 ---")
    plan_result = run_command(["plan", "--daily"])
    print(plan_result.stdout.strip())
    print(DIM + "---------------------------")
    
    print(SUCCESS + "\n壓力測試執行完畢。請檢查上述報告確認系統行為是否符合預期。")

if __name__ == "__main__":
    typer.run(main)
```