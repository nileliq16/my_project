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