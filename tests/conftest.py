"""保证所有 UI 测试只使用测试数据库，不接触用户真实数据。"""

from __future__ import annotations

import os
from pathlib import Path


TEST_DATABASE = Path(__file__).resolve().parent / "runtime" / "app-test.db"
os.environ["GROWTH_OS_DB_PATH"] = str(TEST_DATABASE)
