import re
import json
import logging
import httpx
from bs4 import BeautifulSoup
from config import GDRIVE_FOLDER_ID, META_FILE

logger = logging.getLogger(__name__)

async def fetch_latest_schedule_meta(folder_id: str = GDRIVE_FOLDER_ID) -> dict | None:
    """
    Checks the Google Drive folder for the 1st course schedule file.
    Returns dict with file_id, title, last_modified, or None.
    """
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#grid"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch Google Drive folder: status {resp.status_code}")
                return None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            entries = soup.select(".flip-entry")
            
            for entry in entries:
                title_el = entry.select_one(".flip-entry-title")
                link_el = entry.select_one("a")
                mod_el = entry.select_one(".flip-entry-last-modified")
                
                title = title_el.text.strip() if title_el else ""
                href = link_el.get("href", "") if link_el else ""
                last_modified = mod_el.text.strip() if mod_el else ""
                
                # Check if it's the schedule document (contains 'Розклад' and '1_к' or '1 к')
                # or match any schedule file in this folder
                file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", href)
                file_id = file_id_match.group(1) if file_id_match else None
                
                if file_id and ("розклад" in title.lower() or "doc" in title.lower()):
                    return {
                        "file_id": file_id,
                        "title": title,
                        "last_modified": last_modified,
                        "folder_id": folder_id
                    }
    except Exception as e:
        logger.error(f"Error checking schedule updates: {e}")
    
    return None

def has_schedule_changed(new_meta: dict) -> bool:
    """
    Compares current meta with cached meta in meta.json.
    """
    if not META_FILE.exists():
        return True
    
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            saved_meta = json.load(f)
            
        if saved_meta.get("file_id") != new_meta.get("file_id"):
            return True
        if saved_meta.get("last_modified") != new_meta.get("last_modified"):
            return True
        return False
    except Exception:
        return True

def save_schedule_meta(meta: dict):
    """
    Saves new meta to meta.json.
    """
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
