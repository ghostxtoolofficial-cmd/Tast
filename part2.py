import os
import time
import logging
from flask import Flask, request

CONFIG_DIR = "/storage/emulated/0/Ghost X Tool Manager"

# ==========================================
# 1. SERVER SETUP
# ==========================================
os.environ.pop('WERKZEUG_RUN_MAIN', None)
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.disabled = True

# ==========================================
# 2. QUEUE STATE (หน่วยความจำคิว)
# ==========================================
clients_last_seen = {}
clients_combo_index = {} 
clone_queues = {}
clone_statuses = {}

def init_queue(apps_dict):
    """ฟังก์ชันกวาดรายชื่อทั้งหมดจากไฟล์ txt มาเตรียมจัดคิว"""
    global clone_queues, clone_statuses, clients_combo_index, clients_last_seen
    
    for cid in apps_dict.keys():
        clients_last_seen[cid] = 0
        clients_combo_index[cid] = 0
        
        combo_file = os.path.join(CONFIG_DIR, "AutoSwitch", f"{cid}.txt")
        accounts = []
        if os.path.exists(combo_file):
            with open(combo_file, "r") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
                for line in lines:
                    # ตัดเอาแค่ชื่อบัญชีมาโชว์ (ไม่เอาคุกกี้มาโชว์ให้รกจอ)
                    parts = line.split(':', 1)
                    name = parts[0] if len(parts) > 1 else "Unknown"
                    accounts.append(name)
        
        clone_queues[cid] = accounts
        # ตั้งสถานะทุกคนเป็น WAITING ตั้งแต่เริ่ม
        clone_statuses[cid] = ["WAITING"] * len(accounts) if accounts else []

# ==========================================
# 3. API ENDPOINTS (จุดรับสัญญาณจาก Lua)
# ==========================================
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        clone_id = data.get("clone_id", "clone_1")
        if clone_id == "auto": clone_id = "clone_1"
        
        # อัปเดตเวลาล่าสุดว่าเกมยังไม่ค้าง
        if clone_id in clients_last_seen:
            clients_last_seen[clone_id] = time.time()
    except Exception:
        pass
    return "OK", 200

@app.route('/task_complete', methods=['POST'])
def task_complete():
    try:
        data = request.get_json(force=True, silent=True) or {}
        clone_id = data.get("clone_id", "clone_1")
        if clone_id == "auto": clone_id = "clone_1"

        if clone_id in clone_queues:
            idx = clients_combo_index.get(clone_id, 0)
            total = len(clone_queues[clone_id])
            
            if total > 0:
                # เปลี่ยนสถานะไอดีที่เพิ่งทำเสร็จเป็น DONE
                clone_statuses[clone_id][idx % total] = "DONE"
            
            # บังคับบวกคิวไปบรรทัดถัดไปแบบ 100% ไม่มีเงื่อนไข
            clients_combo_index[clone_id] = idx + 1
            
            # รีเซ็ตเวลาเป็น 0 เพื่อกระตุ้นให้ part3.py ฆ่าแอปแล้วสลับไอดีทันที
            clients_last_seen[clone_id] = 0 
            print(f"\n\033[92m[+] Lua Signal Received! Moving to next queue...\033[0m")
    except Exception:
        pass
    return "OK", 200
    
