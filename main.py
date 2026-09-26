import os
import sys
import time
import threading
import logging
import urllib.request
import json
import requests
import platform
import subprocess
import base64
import hashlib
import hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from flask import Flask, request

CONFIG_DIR = "/storage/emulated/0/Ghost X Tool Manager"
SETTING_FILE = f"{CONFIG_DIR}/Setting.txt"
SQLITE_BIN = "/data/data/com.termux/files/usr/bin/sqlite3"

def load_apps():
    apps = {}
    app_file = os.path.join(CONFIG_DIR, "apps.txt")
    if os.path.exists(app_file):
        with open(app_file, "r") as f:
            lines = f.read().splitlines()
            for i, pkg in enumerate(lines):
                if pkg.strip():
                    apps[f"clone_{i+1}"] = pkg.strip()
    if not apps:
        apps["clone_1"] = "com.roblox.client"
    return apps

def get_settings():
    settings = {"MODE": "NORMAL", "MAP_ID": "", "MAX_CLONES": "ALL", "CHECK_INTERVAL": 30, "TIMEOUT": 40, "LAUNCH_DELAY": 15, "LOOP_DELAY": 60}
    if os.path.exists(SETTING_FILE):
        with open(SETTING_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if k in settings:
                        try:
                            settings[k] = int(v) if v.isdigit() else v
                        except: pass
    return settings

def extract_clean_cookie(raw_text):
    raw_text = raw_text.strip()
    if "_|WARNING" in raw_text: return "_|WARNING" + raw_text.split("_|WARNING", 1)[1]
    if ":" in raw_text: return raw_text.split(":")[-1].strip()
    return raw_text

def get_switch_data(clone_id, clients_combo_index):
    combo_file = os.path.join(CONFIG_DIR, "AutoSwitch", f"{clone_id}.txt")
    curr_line = clients_combo_index.get(clone_id, 0)
    if os.path.exists(combo_file):
        with open(combo_file, "r") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
            if len(lines) == 0: return None, None
            line_data = lines[curr_line % len(lines)]
            parts = line_data.split(':', 1)
            name = parts[0] if len(parts) > 1 else "Unknown"
            return name, extract_clean_cookie(line_data)
    return None, None

def inject_cookie(package_name, clone_id, acc_cookie):
    data_dir = f"/data/data/{package_name}"
    webview_dir = f"{data_dir}/app_webview/Default"
    cookies_db = f"{webview_dir}/Cookies"
    xml_dir = f"{data_dir}/shared_prefs"
    xml_file = f"{xml_dir}/{package_name}_preferences.xml"
    
    os.system(f"su -c 'rm -f {xml_dir}/prefs.xml' > /dev/null 2>&1")
    os.system(f"su -c 'rm -rf {data_dir}/files/appData/LocalStorage/*' > /dev/null 2>&1")
    os.system(f"su -c 'rm -f {xml_dir}/*.xml' > /dev/null 2>&1")
    os.system(f"su -c 'rm -rf {webview_dir}/Local\\ Storage/*' > /dev/null 2>&1")
    os.system(f"su -c 'rm -rf {webview_dir}/Session\\ Storage/*' > /dev/null 2>&1")
    os.system(f"su -c 'rm -rf {webview_dir}/Cache/*' > /dev/null 2>&1")
    
    xml_content = f"<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n    <string name=\".ROBLOSECURITY\">{acc_cookie}</string>\n</map>"
    tmp_xml = f"{CONFIG_DIR}/tmp_xml_{clone_id}.xml"
    with open(tmp_xml, "w") as f: f.write(xml_content)
    
    os.system(f"su -c 'mkdir -p {xml_dir} && cp {tmp_xml} {xml_file} && rm -f {tmp_xml}' > /dev/null 2>&1")
    
    check_db = os.popen(f"su -c 'ls {cookies_db} 2>/dev/null'").read().strip()
    if not check_db:
        os.system(f"su -c 'monkey -p {package_name} -c android.intent.category.LAUNCHER 1' > /dev/null 2>&1")
        time.sleep(7)
        os.system(f"su -c 'am force-stop {package_name}' > /dev/null 2>&1")
        
    os.system(f"su -c 'rm -f {cookies_db}-journal {cookies_db}-wal {cookies_db}-shm' > /dev/null 2>&1")
    
    safe_cookie = acc_cookie.replace("'", "''")
    now = (int(time.time()) + 11644473600) * 1000000
    expires = now + (365 * 24 * 60 * 60 * 1000000)
    sql = f"DELETE FROM cookies; INSERT INTO cookies (creation_utc, top_frame_site_key, host_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, is_same_party) VALUES ({now}, '', '.roblox.com', '.ROBLOSECURITY', '{safe_cookie}', '', '/', {expires}, 1, 1, {now}, 1, 1, 1, -1, 1, 443, 0);"
    
    tmp_sql = f"{CONFIG_DIR}/inject_{clone_id}.sql"
    with open(tmp_sql, "w") as f: f.write(sql)
    
    os.system(f"su -c 'cp {tmp_sql} /data/local/tmp/inject_{clone_id}.sql && chmod 644 /data/local/tmp/inject_{clone_id}.sql' > /dev/null 2>&1")
    os.system(f"su -c '{SQLITE_BIN} {cookies_db} < /data/local/tmp/inject_{clone_id}.sql' > /dev/null 2>&1")
    
    app_uid = os.popen(f"su -c 'stat -c %u {data_dir}' 2>/dev/null").read().strip()
    if app_uid:
        os.system(f"su -c 'chown -R {app_uid}:{app_uid} {data_dir}' > /dev/null 2>&1")
        os.system(f"su -c 'chmod -R 777 {xml_dir}' > /dev/null 2>&1")
    
    os.system(f"su -c 'rm -f /data/local/tmp/inject_{clone_id}.sql && rm -f {tmp_sql}' > /dev/null 2>&1")

class CryptoEnvelope:
    MAX_DRIFT = 300
    def __init__(self, app_secret):
        self.enc_key = hashlib.sha256(("enc:" + app_secret).encode()).digest()
        self.mac_key = hashlib.sha256(("mac:" + app_secret).encode()).digest()
    def encrypt(self, data):
        raw = json.dumps(data).encode()
        iv = os.urandom(16)
        padder = padding.PKCS7(128).padder()
        padded = padder.update(raw) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv)).encryptor()
        ct = encryptor.update(padded) + encryptor.finalize()
        p = base64.b64encode(iv + ct).decode()
        t = int(time.time())
        s = hmac.new(self.mac_key, (p + str(t)).encode(), hashlib.sha256).hexdigest()
        return json.dumps({"p": p, "t": t, "s": s})
    def decrypt(self, envelope_json):
        env = json.loads(envelope_json)
        if not all(k in env for k in ("p", "t", "s")): raise ValueError("Invalid envelope format")
        p, t, s = env["p"], int(env["t"]), env["s"]
        expected = hmac.new(self.mac_key, (p + str(t)).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, s): raise ValueError("HMAC verification failed")
        if abs(int(time.time()) - t) > self.MAX_DRIFT: raise ValueError("Request expired")
        combined = base64.b64decode(p)
        iv, ct = combined[:16], combined[16:]
        decryptor = Cipher(algorithms.AES(self.enc_key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        raw = unpadder.update(padded) + unpadder.finalize()
        return json.loads(raw)

class PWFLicense:
    BASE_URL = "https://pwfauth.com"
    APP_SECRET = "ea3e876c7d3a28937cd5ccd798b85a0d08951a7d89289480f789f9a39fb0eef1"
    KILL_CODES = {"BANNED", "PAUSED", "EXPIRED", "HWID_RESET", "MAINTENANCE", "SESSION_REVOKED", "SESSION_EXPIRED", "SESSION_MISMATCH"}
    MAX_HEARTBEAT_FAILURES = 3

    def __init__(self):
        self.crypto = CryptoEnvelope(self.APP_SECRET)
        self.session = requests.Session()
        self.session.headers.update({"X-App-Secret": self.APP_SECRET, "Content-Type": "application/json"})
        self.session_id = None
        self.license_key = None
        self.heartbeat_interval = 30

    def get_hwid(self):
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_BaseBoard).SerialNumber"], stderr=subprocess.DEVNULL, creationflags=0x08000000)
                serial = out.decode(errors="ignore").strip()
                if serial: return serial
                return platform.node()
            with open("/etc/machine-id") as f: return f.read().strip()
        except Exception: return platform.node()

    def _parse_reply(self, res):
        raw = res.text or ""
        if not raw.strip(): raise RuntimeError(f"HTTP {res.status_code} empty")
        try: probe = json.loads(raw)
        except ValueError: raise RuntimeError(f"HTTP {res.status_code} non-JSON")
        if isinstance(probe, dict) and all(k in probe for k in ("p", "t", "s")): return self.crypto.decrypt(raw)
        if res.status_code >= 400 and not (isinstance(probe, dict) and "success" in probe): raise RuntimeError(f"HTTP {res.status_code}")
        return probe

    def _post(self, endpoint, body):
        encrypted = self.crypto.encrypt(body)
        res = self.session.post(self.BASE_URL + endpoint, data=encrypted, timeout=15)
        return self._parse_reply(res)

    def login(self, license_key):
        result = self._post("/api/auth/login.php", {"license_key": license_key, "hwid": self.get_hwid()})
        if result.get("success"):
            self.session_id = result.get("session_id")
            self.license_key = license_key
            self.heartbeat_interval = int(result.get("heartbeat_interval", 30))
        return result

    def check_key(self, license_key):
        return self._post("/api/auth/check-key.php", {"license_key": license_key})

    def heartbeat(self):
        if not self.session_id: return None
        return self._post("/api/auth/heartbeat.php", {"session_id": self.session_id, "license_key": self.license_key})

    def run_heartbeat(self, on_revoked):
        failures = 0
        while self.session_id:
            time.sleep(self.heartbeat_interval)
            try: r = self.heartbeat()
            except Exception: r = None
            if r is None:
                if not self.session_id: return
                failures += 1
                if failures >= self.MAX_HEARTBEAT_FAILURES:
                    self.session_id = None
                    on_revoked("NETWORK_LOST", "Cannot reach the license server.")
                    return
                continue
            failures = 0
            if r.get("success"): continue
            code = r.get("error_code", "")
            if code in self.KILL_CODES:
                self.session_id = None
                on_revoked(code, r.get("message", ""))
                return

    def _get(self, endpoint, bearer_key=None):
        headers = {"Authorization": "Bearer " + bearer_key} if bearer_key else {}
        res = self.session.get(self.BASE_URL + endpoint, headers=headers, timeout=15)
        return self._parse_reply(res)

    def _post_plain(self, endpoint, body):
        res = self.session.post(self.BASE_URL + endpoint, data=json.dumps(body), timeout=15)
        return self._parse_reply(res)

    def get_app_info(self): return self._get("/api/app/info.php")
    def get_texts(self): return self._get("/api/app/text.php", self.license_key)
    def get_slides(self): return self._post("/api/app/slides.php", {"action": "get_slides"})
    def check_update(self, current_version): return self._post("/api/update/check.php", {"v": current_version, "channel": "stable", "hwid": self.get_hwid(), "license_key": self.license_key})
    def track_social_click(self, link_id): return self._post("/api/app/social-click.php", {"link_id": link_id})
    def create_trial(self): return self._post_plain("/api/auth/trial.php", {"hwid": self.get_hwid()})
    def request_hwid_reset(self, reason): return self._post_plain("/api/auth/request-hwid-reset.php", {"license_key": self.license_key, "reason": reason})
    def register_account(self, username, password, email): return self._post_plain("/api/auth/account-register.php", {"username": username, "password": password, "email": email})
    def login_account(self, username, password):
        result = self._post_plain("/api/auth/account-login.php", {"username": username, "password": password, "hwid": self.get_hwid()})
        if result.get("success"):
            self.session_id = result.get("session_id")
            self.license_key = result.get("license_key", self.license_key)
        return result
    def change_account_password(self, username, current_password, new_password): return self._post_plain("/api/auth/change-password.php", {"username": username, "current_password": current_password, "new_password": new_password})
    def get_pricing(self): return self._get("/api/app/pricing.php?app_id=8f5c522f-3e72-4078-b3ed-f7c6dd364f8d")
    def logout(self):
        if not self.session_id: return None
        result = self._post("/api/auth/logout.php", {"session_id": self.session_id, "license_key": self.license_key})
        self.session_id = None
        return result

    def verify_license():
    LICENSE_FILE = os.path.join(CONFIG_DIR, "license.key")
    if not os.path.exists(LICENSE_FILE):
        print("\033[91m [!] No License Key found!\033[0m")
        sys.exit(1)
    with open(LICENSE_FILE, "r") as f:
        user_key = f.read().strip()
    client = PWFLicense()
    result = client.login(user_key)
    if not result.get("success"):
        print("\033[91m [-] Authentication Failed\033[0m")
        os.remove(LICENSE_FILE)
        sys.exit(1)
    def on_revoked(code, message):
        print("\n\033[91m [!] LICENSE REVOKED / EXPIRED \033[0m")
        os._exit(0)
    threading.Thread(target=client.run_heartbeat, args=(on_revoked,), daemon=True).start()
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
    clients_last_seen[cid] = 0
    clients_retry_count[cid] = 0
    clients_usernames[cid] = cid 
    clients_combo_index[cid] = 0

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
    if not username or username == "Unknown": return None
    uname_lower = username.lower()
    for cid, exp_name in clients_expected_names.items():
        if exp_name == uname_lower: return cid
    for cid, uname in clients_usernames.items():
        if uname.lower() == uname_lower and uname != cid: return cid
    curr = time.time()
    for cid in APPS_PACKAGE_NAMES.keys():
        seen = clients_last_seen.get(cid, 0)
        if seen == 0 or (curr - seen) > cfg["TIMEOUT"]: return cid
    return list(APPS_PACKAGE_NAMES.keys())[0]

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    username = data.get("username") 
    cfg = get_settings()
    clone_id = resolve_clone_id(data.get("clone_id"), username, cfg)
    if not clone_id: return "WAIT", 200
    if cfg["MODE"] == "AUTO_SWITCH":
        expected_name, _ = get_switch_data(clone_id, clients_combo_index)
        if username and expected_name and expected_name != "Unknown" and username.lower() != expected_name.lower():
            clients_last_seen[clone_id] = 0
            return "MISMATCH", 200
    clients_last_seen[clone_id] = time.time()
    clients_retry_count[clone_id] = 0 
    if username and username != "Unknown": clients_usernames[clone_id] = username
    return "OK", 200

@app.route('/task_complete', methods=['POST'])
def task_complete():
    clone_id = resolve_clone_id(request.json.get("clone_id"), request.json.get("username"), get_settings())
    if clone_id and get_settings()["MODE"] == "AUTO_SWITCH":
        clients_combo_index[clone_id] = clients_combo_index.get(clone_id, 0) + 1
        clients_last_seen[clone_id] = 0 
    return "OK", 200

def print_ui(cfg, current_time):
    sys.stdout.write(f"\033[H\033[J")
    print(f"{CYAN}========================================{RESET}")
    print(f"{WHITE}             SYSTEM STATUS              {RESET}")
    print(f"{CYAN}========================================{RESET}")
    online_count = sum(1 for cid in APPS_PACKAGE_NAMES if clients_last_seen.get(cid, 0) != 0 and (current_time - clients_last_seen[cid]) <= cfg["TIMEOUT"])
    print(f" [Active Clones] : {WHITE}{online_count} / {len(APPS_PACKAGE_NAMES)}{RESET}")
    print(f"{CYAN}----------------------------------------{RESET}")
    for cid in APPS_PACKAGE_NAMES.keys():
        l_seen = clients_last_seen.get(cid, 0)
        d_name = clients_usernames.get(cid, cid)
        if l_seen == 0 or (current_time - l_seen) > cfg["TIMEOUT"]: print(f"{RED} [-] {d_name} : OFFLINE{RESET}")
        else: print(f"{GREEN} [+] {d_name} : ONLINE{RESET}")
    print(f"{CYAN}========================================{RESET}\n")

def countdown(t, msg):
    for i in range(t, 0, -1):
        sys.stdout.write(f"\r{YELLOW} [>] {msg} : {i}s remaining...{RESET}   ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write(f"\r{' ' * 50}\r") 
    sys.stdout.flush()

def auto_rejoin_checker():
    time.sleep(1) 
    while True:
        current_time = time.time()
        cfg = get_settings()
        if cfg["MODE"] == "AUTO_SWITCH":
            for cid in APPS_PACKAGE_NAMES.keys():
                acc_name, _ = get_switch_data(cid, clients_combo_index)
                if acc_name and acc_name != "Unknown" and cid not in clients_expected_names:
                    clients_usernames[cid] = acc_name
                    clients_expected_names[cid] = acc_name.lower()
        else:
            cookie_file = os.path.join(CONFIG_DIR, "cookie.txt")
            if os.path.exists(cookie_file):
                with open(cookie_file, "r") as f: cookies = f.read().splitlines()
                for i, cid in enumerate(APPS_PACKAGE_NAMES.keys()):
                    if i < len(cookies) and cookies[i].strip() and cid not in clients_expected_names:
                        sys.stdout.write(f"\r{WHITE} [>] Fetching API profile for {cid}...{' ' * 10}\r")
                        sys.stdout.flush()
                        uname = fetch_roblox_name(cookies[i])
                        if uname:
                            clients_usernames[cid] = uname
                            clients_expected_names[cid] = uname.lower()
        
        print_ui(cfg, current_time)
        sys.stdout.write(f"{WHITE} [>] Initiating system scan...{RESET}\n")
        time.sleep(0.5)
        
        offline_clones = []
        for clone_id in APPS_PACKAGE_NAMES.keys():
            sys.stdout.write(f"\r{WHITE} [>] Verifying {clone_id}...{' ' * 10}\r")
            sys.stdout.flush()
            time.sleep(0.3) 
            last_seen = clients_last_seen.get(clone_id, 0)
            d_name = clients_usernames.get(clone_id, clone_id)
            if last_seen == 0 or (current_time - last_seen) > cfg["TIMEOUT"]:
                sys.stdout.write(f"{RED} [-] {clone_id} ({d_name}) is OFFLINE{' ' * 10}{RESET}\n")
                offline_clones.append(clone_id)
            else:
                sys.stdout.write(f"{GREEN} [+] {clone_id} ({d_name}) is ONLINE{' ' * 10}{RESET}\n")
        
        print(f"{CYAN}----------------------------------------{RESET}")
        action_taken = False
        for clone_id in offline_clones:
            retry_count = clients_retry_count.get(clone_id, 0)
            package_name = APPS_PACKAGE_NAMES.get(clone_id)
            if retry_count < MAX_RETRIES:
                d_name = clients_usernames.get(clone_id, clone_id)
                print(f"{YELLOW} [!] Recovering {clone_id} ({d_name}) (Attempt {retry_count + 1}/{MAX_RETRIES}){RESET}")
                os.system(f"su -c 'am force-stop {package_name}' > /dev/null 2>&1")
                time.sleep(1)
                if cfg["MODE"] == "AUTO_SWITCH":
                    acc_name, acc_cookie = get_switch_data(clone_id, clients_combo_index)
                    if acc_cookie: inject_cookie(package_name, clone_id, acc_cookie)
                
                if cfg["MAP_ID"]: os.system(f"su -c 'am start -a android.intent.action.VIEW -d \"roblox://placeId={cfg['MAP_ID']}\" -p {package_name}' > /dev/null 2>&1")
                else: os.system(f"su -c 'monkey -p {package_name} -c android.intent.category.LAUNCHER 1' > /dev/null 2>&1")
                    
                time.sleep(4) 
                try: c_idx = int(clone_id.split('_')[1])
                except: c_idx = 1
                arrange_window(package_name, c_idx)
                clients_last_seen[clone_id] = time.time() + 45 
                clients_retry_count[clone_id] = retry_count + 1
                action_taken = True
                if cfg["LAUNCH_DELAY"] > 0: countdown(cfg["LAUNCH_DELAY"], f"Boot Delay ({clone_id})")
            else:
                print(f"{RED} [!] {clone_id} suspended for 5 mins (Max retries reached).{RESET}")
                clients_last_seen[clone_id] = time.time() + 300 

        if action_taken: print(f"{CYAN}----------------------------------------{RESET}")
        countdown(cfg["LOOP_DELAY"], "Next system scan in")

if __name__ == '__main__':
    verify_license()
    threading.Thread(target=auto_rejoin_checker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
    
