import os
import sys
import time
import threading
import logging
import urllib.request
import json
from flask import Flask, request

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

clients_last_seen = {}
clients_retry_count = {}
clients_usernames = {} 
clients_combo_index = {} 
clients_expected_names = {} 
APPS_PACKAGE_NAMES = load_apps()
MAX_RETRIES = 3
GREEN, RED, CYAN, WHITE, YELLOW, RESET = '\033[92m', '\033[91m', '\033[96m', '\033[97m', '\033[93m', '\033[0m'

for cid in APPS_PACKAGE_NAMES.keys():
    clients_last_seen[cid], clients_retry_count[cid], clients_usernames[cid], clients_combo_index[cid] = 0, 0, cid, 0

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

def resolve_clone_id(provided_id, username, cfg):
    if provided_id != "auto": return provided_id
    if not username or username == "Unknown": return list(APPS_PACKAGE_NAMES.keys())[0]
    return list(APPS_PACKAGE_NAMES.keys())[0]

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username") 
        cfg = get_settings()
        clone_id = resolve_clone_id(data.get("clone_id"), username, cfg)
        if not clone_id: return "WAIT", 200
        clients_last_seen[clone_id] = time.time()
        clients_retry_count[clone_id] = 0 
        if username and username != "Unknown": clients_usernames[clone_id] = username
    except Exception: pass
    return "OK", 200

@app.route('/task_complete', methods=['POST'])
def task_complete():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username")
        cfg = get_settings()
        if cfg["MODE"] == "AUTO_SWITCH":
            print(f"\n{GREEN}[+] Lua Signal Received! Switching to next account instantly...{RESET}")
            for cid in APPS_PACKAGE_NAMES.keys():
                clients_combo_index[cid] = clients_combo_index.get(cid, 0) + 1
                clients_last_seen[cid] = 0  # สั่งรีเซ็ตสถานะเพื่อบังคับเปลี่ยนไอดีและดึงคุกกี้บรรทัดถัดไปทันที
    except Exception: pass
    return "OK", 200

def print_ui(cfg, current_time):
    sys.stdout.write(f"\033[H\033[J")
    print(f"{CYAN}========================================{RESET}")
    print(f"{WHITE}         GHOST X - FAST SWITCH          {RESET}")
    print(f"{CYAN}========================================{RESET}")
    for cid in APPS_PACKAGE_NAMES.keys():
        l_seen = clients_last_seen.get(cid, 0)
        d_name = clients_usernames.get(cid, cid)
        if l_seen == 0 or (current_time - l_seen) > cfg["TIMEOUT"]: print(f"{RED} [-] {d_name} : OFFLINE / SWITCHING...{RESET}")
        else: print(f"{GREEN} [+] {d_name} : ONLINE{RESET}")
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
            
            if last_seen == 0 or (current_time - last_seen) > cfg["TIMEOUT"]:
                retry_count = clients_retry_count.get(clone_id, 0)
                if retry_count < MAX_RETRIES:
                    os.system(f"su -c 'am force-stop {package_name}' > /dev/null 2>&1")
                    time.sleep(2) 
                    
                    if cfg["MODE"] == "AUTO_SWITCH":
                        sys.stdout.write(f"{YELLOW} [>] Pre-checking account data for {clone_id} (Index: {clients_combo_index.get(clone_id, 0)})...{RESET}\n")
                        acc_name, acc_cookie = get_switch_data(clone_id, clients_combo_index)
                        
                        if acc_cookie:
                            api_name = fetch_roblox_name(acc_cookie)
                            if not api_name:
                                print(f"{RED} [!] Dead Cookie detected. Skipping to next account instantly.{RESET}")
                                clients_combo_index[clone_id] = clients_combo_index.get(clone_id, 0) + 1
                                clients_last_seen[clone_id] = 0
                                continue 
                            
                            clients_usernames[clone_id] = api_name
                            clients_expected_names[clone_id] = api_name.lower()
                            print(f"{GREEN} [+] Injecting valid cookie for: {api_name}{RESET}")
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
                    print(f"{RED} [!] {clone_id} max retries reached. Suspending.{RESET}")
                    clients_last_seen[clone_id] = time.time() + 300 
        
        time.sleep(1)

if __name__ == '__main__':
    verify_license()
    threading.Thread(target=auto_rejoin_checker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
    
