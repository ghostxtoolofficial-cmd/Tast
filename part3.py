import os
import sys
import time
import threading

# ดึงความสามารถจาก part1 และ part2 มารวมร่างกัน
from part1 import load_apps, get_settings, get_switch_data, inject_cookie
from part2 import app, init_queue, clients_last_seen, clients_combo_index, clone_queues, clone_statuses

GREEN, RED, CYAN, WHITE, YELLOW, RESET = '\033[92m', '\033[91m', '\033[96m', '\033[97m', '\033[93m', '\033[0m'
MAX_RETRIES = 3

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

def print_ui(cfg, apps_dict, current_time):
    sys.stdout.write(f"\033[H\033[J")
    print(f"{CYAN}========================================{RESET}")
    print(f"{WHITE}       GHOST X - QUEUE MANAGER          {RESET}")
    print(f"{CYAN}========================================{RESET}")
    
    for cid in apps_dict.keys():
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
            
            for i in range(total):
                acc_name = queue[i]
                stat = statuses[i]
                if stat == "DONE":
                    color, stat_text = GREEN, "[ DONE ]"
                elif stat == "FAILED":
                    color, stat_text = RED, "[ FAILED ]"
                elif i == (curr_idx % total):
                    color, stat_text = YELLOW, "[ RUNNING ]"
                    statuses[i] = "RUNNING"
                else:
                    color, stat_text = WHITE, "[ WAITING ]"
                print(f" {color}{i+1}. {acc_name[:15]:<15} -> {stat_text}{RESET}")
        else:
            if l_seen == 0 or (current_time - l_seen) > cfg["TIMEOUT"]:
                print(f"{RED} [-] {cid} : OFFLINE / RESTARTING...{RESET}")
            else:
                print(f"{GREEN} [+] {cid} : ONLINE{RESET}")
                
    print(f"{CYAN}========================================{RESET}\n")

def auto_rejoin_checker(apps_dict):
    time.sleep(1) 
    clients_retry_count = {cid: 0 for cid in apps_dict.keys()}
    
    while True:
        current_time = time.time()
        cfg = get_settings()
        print_ui(cfg, apps_dict, current_time)
        
        for clone_id, package_name in apps_dict.items():
            last_seen = clients_last_seen.get(clone_id, 0)
            
            if last_seen == 0 or (current_time - last_seen) > cfg["TIMEOUT"]:
                retry_count = clients_retry_count.get(clone_id, 0)
                
                # ถ้าระบบค้างเพราะ Timeout ให้ตั้งสถานะเป็น FAILED แล้วข้ามคิว
                if cfg["MODE"] == "AUTO_SWITCH" and last_seen != 0 and (current_time - last_seen) > cfg["TIMEOUT"]:
                    total = len(clone_queues.get(clone_id, []))
                    idx = clients_combo_index.get(clone_id, 0)
                    if total > 0:
                        clone_statuses[clone_id][idx % total] = "FAILED"
                        clients_combo_index[clone_id] += 1
                        retry_count = 0
                
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
                            # ฉีดคุกกี้เลยโดยไม่ต้องรอเช็คชื่อจากเน็ต เพื่อความไวและกันเกมเด้ง
                            inject_cookie(package_name, clone_id, acc_cookie)
                    
                    if cfg["MAP_ID"]:
                        os.system(f"su -c 'am start -a android.intent.action.VIEW -d \"roblox://placeId={cfg['MAP_ID']}\" -p {package_name}' > /dev/null 2>&1")
                    else:
                        os.system(f"su -c 'monkey -p {package_name} -c android.intent.category.LAUNCHER 1' > /dev/null 2>&1")
                    
                    time.sleep(4) 
                    try: 
                        c_idx = int(clone_id.split('_')[1])
                    except: 
                        c_idx = 1
                    arrange_window(package_name, c_idx)
                    
                    clients_last_seen[clone_id] = time.time() + 30 
                    clients_retry_count[clone_id] = retry_count + 1
                else:
                    # ถ้ารีสตาร์ทเกิน MAX_RETRIES ให้ข้ามคิวทิ้งไปเลย
                    if cfg["MODE"] == "AUTO_SWITCH":
                        idx = clients_combo_index.get(clone_id, 0)
                        total = len(clone_queues.get(clone_id, []))
                        if total > 0: 
                            clone_statuses[clone_id][idx % total] = "FAILED"
                        clients_combo_index[clone_id] += 1
                        clients_last_seen[clone_id] = 0
                        clients_retry_count[clone_id] = 0
        
        time.sleep(1)

if __name__ == '__main__':
    APPS_PACKAGE_NAMES = load_apps()
    init_queue(APPS_PACKAGE_NAMES)
    
    # เปิดระบบตรวจสอบ (Checker) ให้ทำงานคู่ขนานกับ Server
    threading.Thread(target=auto_rejoin_checker, args=(APPS_PACKAGE_NAMES,), daemon=True).start()
    
    # รัน Server 
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
    
