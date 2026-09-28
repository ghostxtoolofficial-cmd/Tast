import os
import sys
import time
import threading
import logging
import urllib.request
import json
from flask import Flask, request

# ดึงตัวแปรจากไฟล์หลัก (ในกรณีที่รวมไฟล์เป็น main.py แล้ว)
try:
    from part1 import load_apps, get_settings, get_switch_data, inject_cookie, CONFIG_DIR
    from part2 import PWFLicense
except ImportError:
    pass

def verify_license():
    return True

os.environ.pop('WERKZEUG_RUN_MAIN', None)
os.environ.pop('WERKZEUG_SERVER_FD', None)
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.disabled = True
try:
    import flask.cli
    flask.cli.show_server_banner = lambda *args: None
except: pass

# --- GLOBAL QUEUE SYSTEM ---
clients_last_seen = {}
clients_retry_count = {}
clients_combo_index = {} 
clone_queues = {}
clone_statuses = {}

APPS_PACKAGE_NAMES = load_apps() if 'load_apps' in globals() else {}
MAX_RETRIES = 3
GREEN, RED, CYAN, WHITE, YELLOW, RESET = '\033[92m', '\033[91m', '\033[96m', '\033[97m', '\033[93m', '\033[0m'

# ฟังก์ชันดึงรายชื่อทั้งหมดขึ้นมาโชว์ตอนเริ่มระบบ
def load_queue_data(clone_id):
    combo_file = os.path.join(CONFIG_DIR, "AutoSwitch", f"{clone_id}.txt")
    accounts = []
    if os.path.exists(combo_file):
        with open(combo_file, "r") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
            for line in lines:
                parts = line.split(':', 1)
                name = parts[0] if len(parts) > 1 else "Unknown"
                accounts.append(name)
    return accounts

# โหลดข้อมูลใส่หน่วยความจำ
for cid in APPS_PACKAGE_NAMES.keys():
    clients_last_seen[cid] = 0
    clients_retry_count[cid] = 0
    clients_combo_index[cid] = 0
    clone_queues[cid] = load_queue_data(cid)
    clone_statuses[cid] = ["WAITING"] * len(clone_queues[cid]) if clone_queues[cid] else []

def arrange_window(package_name, clone_index):
    W, H, COLS = 360, 480, 2
    row = (clone_index - 1) // COLS
    col = (clone_index - 1) % COLS
    left, top = col * W, row * H
    right, bottom = left + W, top + H
    cmd = f"su -c \"dumpsys activity tasks | grep '{package_name}' | grep -o 'taskId=[0-9]*' | cut -d'=' -f2 | head -n 1\""
    task_id = os.popen(cmd).read().strip()
    if task_id and task_id.isdigit():
        os.system(f"su -c 'am task resize {task_id} {left} {top} {right} {bottom}' > /dev/null 2>&1")

def fetch_roblox_name(cookie_str):
    try:
        cookie_str = cookie_str.strip()
        if not cookie_str: return None
        if "_|WARNING" in cookie_str: cookie_str = "_|WARNING" + cookie_str.split("_|WARNING", 1)[1]
        req = urllib.request.Request("https://users.roblox.com/v1/users/authenticated")
        req.add_header("Cookie", f".ROBLOSECURITY={cookie_str}")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode('utf-8')).get("name")
    except: return None

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        clone_id = data.get("clone_id")
        if clone_id == "auto": clone_id = list(APPS_PACKAGE_NAMES.keys())[0]
        if clone_id in APPS_PACKAGE_NAMES:
            clients_last_seen[clone_id] = time.time()
            clients_retry_count[clone_id] = 0 
    except Exception: pass
    return "OK", 200

@app.route('/task_complete', methods=['POST'])
def task_complete():
    try:
        data = request.get_json(force=True, silent=True) or {}
        cfg = get_settings()
        clone_id = data.get("clone_id")
        if clone_id == "auto": clone_id = list(APPS_PACKAGE_NAMES.keys())[0]

        if clone_id in APPS_PACKAGE_NAMES and cfg["MODE"] == "AUTO_SWITCH":
            idx = clients_combo_index[clone_id]
            total = len(clone_queues[clone_id])
            if total > 0:
                clone_statuses[clone_id][idx % total] = "DONE" # สั่งจบงานบัญชีนี้
            
            clients_combo_index[clone_id] += 1 # บังคับข้ามไปบรรทัดต่อไป
            clients_last_seen[clone_id] = 0 # รีเซ็ตเวลาเพื่อเปลี่ยนไอดีทันที
    except Exception: pass
    return "OK", 200

def print_ui(cfg, current_time):
    sys.stdout.write(f"\033[H\033[J")
    print(f"{CYAN}========================================{RESET}")
    print(f"{WHITE}       GHOST X - QUEUE MANAGER          {RESET}")
    print(f"{CYAN}========================================{RESET}")
    
    for cid in APPS_PACKAGE_NAMES.keys():
        l_seen = clients_last_seen.get(cid, 0)
        
        if cfg["MODE"] == "AUTO_SWITCH":
            queue = clone_queues.get(cid, [])
            statuses = clone_statuses.get(cid, [])
            total = len(queue)
            curr_idx = clients_combo_index.get(cid, 0)
            
            if total == 0:
                print(f"{RED} [!] No accounts found in {cid}.txt{RESET}")
                continue
                
            print(f"{WHITE} [ Clone: {cid} | Total Accounts: {total} ]{RESET}")
            print(f"{CYAN}----------------------------------------{RESET}")
            
            # ระบบแสดงสถานะบัญชีทั้งหมด
            for i in range(total):
                acc_name = queue[i]
                stat = statuses[i]
                
                # กำหนดสีและคำตามสถานะ
                if stat == "DONE":
                    color, stat_text = GREEN, "[ DONE ]"
                elif stat == "FAILED":
                    color, stat_text = RED, "[ FAILED ]"
                elif i == (curr_idx % total):
                    color, stat_text = YELLOW, "[ RUNNING ]"
                    statuses[i] = "RUNNING" # อัปเดต State ชั่วคราว
                else:
                    color, stat_text = WHITE, "[ WAITING ]"
                    
                print(f" {color}{i+1}. {acc_name[:15]:<15} -> {stat_text}{RESET}")
            
        else:
            if l_seen == 0 or (current_time - l_seen) > cfg["TIMEOUT"]: print(f"{RED} [-] {cid} : OFFLINE / RESTARTING...{RESET}")
            else: print(f"{GREEN} [+] {cid} : ONLINE{RESET}")
                
    print(f"{CYAN}========================================{RESET}\n")

def auto_rejoin_checker():
    time.sleep(1) 
    while True:
        current_time = time.time()
        cfg = get_settings()
        print_ui(cfg, current_time)
        
        for clone_id in APPS_PACKAGE_NAMES.keys():
            last_seen = clients_last_seen.get(clone_id, 0)
            package_name = APPS_PACKAGE_NAMES.get(clone_id)
            
            # เมื่อไอดีหยุดทำงาน หรือเกมค้างเกินเวลา TIMEOUT
            if last_seen == 0 or (current_time - last_seen) > cfg["TIMEOUT"]:
                retry_count = clients_retry_count.get(clone_id, 0)
                
                if cfg["MODE"] == "AUTO_SWITCH":
                    total = len(clone_queues.get(clone_id, []))
                    idx = clients_combo_index.get(clone_id, 0)
                    
                    # ถ้าระบบค้างเพราะ Timeout (ไม่ใช่การปิดปกติจาก /task_complete)
                    if last_seen != 0 and (current_time - last_seen) > cfg["TIMEOUT"]:
                        if total > 0:
                            clone_statuses[clone_id][idx % total] = "FAILED"
                            clients_combo_index[clone_id] += 1 # ข้ามไปไอดีต่อไป
                            retry_count = 0 # รีเซ็ตการนับรีสตาร์ทเพื่อไอดีใหม่
                            
                if retry_count < MAX_RETRIES:
                    os.system(f"su -c 'am force-stop {package_name}' > /dev/null 2>&1")
                    time.sleep(2) 
                    
                    if cfg["MODE"] == "AUTO_SWITCH":
                        total = len(clone_queues.get(clone_id, []))
                        if total == 0:
                            time.sleep(5)
                            continue
                            
                        idx = clients_combo_index.get(clone_id, 0)
                        acc_name, acc_cookie = get_switch_data(clone_id, clients_combo_index)
                        
                        if acc_cookie:
                            clone_statuses[clone_id][idx % total] = "RUNNING"
                            api_name = fetch_roblox_name(acc_cookie)
                            
                            # ถ้าคุกกี้ตาย ข้ามคิวทันที
                            if not api_name:
                                clone_statuses[clone_id][idx % total] = "FAILED"
                                clients_combo_index[clone_id] += 1
                                clients_last_seen[clone_id] = 0
                                continue 
                            
                            inject_cookie(package_name, clone_id, acc_cookie)
                    
                    if cfg["MAP_ID"]: os.system(f"su -c 'am start -a android.intent.action.VIEW -d \"roblox://placeId={cfg['MAP_ID']}\" -p {package_name}' > /dev/null 2>&1")
                    else: os.system(f"su -c 'monkey -p {package_name} -c android.intent.category.LAUNCHER 1' > /dev/null 2>&1")
                    
                    time.sleep(4) 
                    try: c_idx = int(clone_id.split('_')[1])
                    except: c_idx = 1
                    arrange_window(package_name, c_idx)
                    
                    clients_last_seen[clone_id] = time.time() + 30 
                    clients_retry_count[clone_id] = retry_count + 1
                else:
                    # ถ้ารีสตาร์ทจนครบโควต้าแล้ว ให้ข้ามคิวไปเลย ไม่ต้องหยุดรอ
                    if cfg["MODE"] == "AUTO_SWITCH":
                        idx = clients_combo_index.get(clone_id, 0)
                        total = len(clone_queues.get(clone_id, []))
                        if total > 0: clone_statuses[clone_id][idx % total] = "FAILED"
                        clients_combo_index[clone_id] += 1
                        clients_last_seen[clone_id] = 0
                        clients_retry_count[clone_id] = 0
        
        time.sleep(1)

if __name__ == '__main__':
    verify_license()
    threading.Thread(target=auto_rejoin_checker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
    
