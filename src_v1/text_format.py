import html
import re

def format_text(text: str) -> str:
    # Escape HTML
    safe = html.escape(text)
    # ตัวหนา **...**
    safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
    # ตัวเอียง *...*
    safe = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe)
    # Bullet/numbered list: 1. ... 2. ... 3. ...
    safe = re.sub(r'(\d+)\. ', r'<br><b>\1.</b> ', safe)
    # ขึ้นบรรทัดใหม่หลัง "เช่น:" หรือ "ค่ะ", "ครับ"
    # safe = re.sub(r'(เช่น:|ค่ะ|ครับ)', r'\1<br>', safe)
    # เปลี่ยน \n เป็น <br>
    safe = safe.replace('\n', '<br>')
    # ตัดช่องว่างหัวท้าย
    safe = safe.strip()
    return safe