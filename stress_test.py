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