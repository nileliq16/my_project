# tests/test_scheduler.py

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 將專案根目錄添加到 Python 路徑中，以便 pytest 可以找到 scheduler 模組
# 假設 tests/ 目錄與 scheduler.py 在同一個父目錄下
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scheduler import update_review_schedule, LEITNER_INTERVALS

def test_update_schedule_good_performance_move_to_next_box():
    """
    測試 'good' 表現，任務從一個盒子移動到下一個盒子。
    """
    today = datetime.now().date()
    # 假設任務目前在第 2 個盒子 (間隔 3 天)
    task = {
        "task_id": 1,
        "review_interval": LEITNER_INTERVALS[1] # 3
    }
    
    updated_task = update_review_schedule(task, "good")
    
    expected_interval = LEITNER_INTERVALS[2] # 7
    expected_next_review_date = today + timedelta(days=expected_interval)

    assert updated_task['last_review_date'] == today.isoformat()
    assert updated_task['review_interval'] == expected_interval
    assert updated_task['next_review_date'] == expected_next_review_date.isoformat()


def test_update_schedule_ok_performance_from_start():
    """
    測試 'ok' 表現，任務從未複習過 (間隔 0) 開始。
    """
    today = datetime.now().date()
    task = {
        "task_id": 2,
        "review_interval": 0
    }
    
    updated_task = update_review_schedule(task, "ok")
    
    expected_interval = LEITNER_INTERVALS[0] # 1
    expected_next_review_date = today + timedelta(days=expected_interval)

    assert updated_task['last_review_date'] == today.isoformat()
    assert updated_task['review_interval'] == expected_interval
    assert updated_task['next_review_date'] == expected_next_review_date.isoformat()


def test_update_schedule_bad_performance_reset_to_first_box():
    """
    測試 'bad' 表現，任務從任何盒子重設回第一個盒子。
    """
    today = datetime.now().date()
    # 假設任務已在第 4 個盒子 (間隔 14 天)
    task = {
        "task_id": 3,
        "review_interval": LEITNER_INTERVALS[3] # 14
    }
    
    updated_task = update_review_schedule(task, "bad")
    
    expected_interval = LEITNER_INTERVALS[0] # 1
    expected_next_review_date = today + timedelta(days=expected_interval)

    assert updated_task['last_review_date'] == today.isoformat()
    assert updated_task['review_interval'] == expected_interval
    assert updated_task['next_review_date'] == expected_next_review_date.isoformat()

def test_update_schedule_good_performance_at_last_box():
    """
    測試 'good' 表現，當任務已在最後一個盒子時，間隔保持不變。
    """
    today = datetime.now().date()
    task = {
        "task_id": 4,
        "review_interval": LEITNER_INTERVALS[-1] # 30
    }
    
    updated_task = update_review_schedule(task, "good")
    
    expected_interval = LEITNER_INTERVALS[-1] # 30
    expected_next_review_date = today + timedelta(days=expected_interval)

    assert updated_task['last_review_date'] == today.isoformat()
    assert updated_task['review_interval'] == expected_interval
    assert updated_task['next_review_date'] == expected_next_review_date.isoformat()