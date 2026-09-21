from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATASOURCE_FILE = BASE_DIR / 'datasources.json'
FIX_HISTORY_FILE = BASE_DIR / 'fix_history.json'

TARGET_COLLATION = 'utf8mb4_0900_ai_ci'
TARGET_CHARSET = 'utf8mb4'
MAX_ROWS_THRESHOLD = 100000
