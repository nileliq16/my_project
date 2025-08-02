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