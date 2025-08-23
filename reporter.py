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