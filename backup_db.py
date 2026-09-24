#!/usr/bin/env python3
"""
VertaFlow — Safe Automated SQLite Database Backup Engine
========================================================
Uses SQLite's native online backup API (safe under concurrent WAL writes).
Performs automatic backup rotation (retains last 14 backups).
"""

import os
import sys
import glob
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("VertaBackup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vertaflow.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MAX_BACKUPS_TO_KEEP = 14

def ensure_backup_dir():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)

def run_backup() -> str:
    """
    Safely creates an online atomic backup of vertaflow.db.
    Returns path to created backup file.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_filename = f"vertaflow_backup_{timestamp}.db"
    target_path = os.path.join(BACKUP_DIR, target_filename)

    source_conn = None
    target_conn = None
    try:
        source_conn = sqlite3.connect(DB_PATH, timeout=30.0)
        target_conn = sqlite3.connect(target_path)
        source_conn.backup(target_conn)
        target_conn.close()
        source_conn.close()
        file_size_kb = os.path.getsize(target_path) / 1024
        logger.info(f"✅ DB zaxirasi muvaffaqiyatli saqlandi: {target_filename} ({file_size_kb:.1f} KB)")
        rotate_backups()
        return target_path
    except Exception as e:
        logger.error(f"❌ DB zaxiralashda xatolik: {e}")
        if target_conn:
            try: target_conn.close()
            except Exception: pass
        if source_conn:
            try: source_conn.close()
            except Exception: pass
        if os.path.exists(target_path) and os.path.getsize(target_path) == 0:
            os.remove(target_path)
        raise e

def rotate_backups():
    """Deletes older backup files keeping only the most recent MAX_BACKUPS_TO_KEEP."""
    try:
        backups = sorted(
            glob.glob(os.path.join(BACKUP_DIR, "vertaflow_backup_*.db")),
            key=os.path.getmtime
        )
        if len(backups) > MAX_BACKUPS_TO_KEEP:
            to_remove = backups[:-MAX_BACKUPS_TO_KEEP]
            for old_file in to_remove:
                os.remove(old_file)
                logger.info(f"🗑️ Eski zaxira tozalandi: {os.path.basename(old_file)}")
    except Exception as e:
        logger.warning(f"Zaxiralarni tozalashda ogohlantirish: {e}")

if __name__ == "__main__":
    path = run_backup()
    print(f"Backup created at: {path}")
