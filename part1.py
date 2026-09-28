import os
import time

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
                        try: settings[k] = int(v) if v.isdigit() else v
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
    
    os.system(f"su -c 'rm -f {xml_dir}/prefs.xml {xml_dir}/*.xml' > /dev/null 2>&1")
    os.system(f"su -c 'rm -rf {data_dir}/files/appData/LocalStorage/* {webview_dir}/Local\\ Storage/* {webview_dir}/Session\\ Storage/* {webview_dir}/Cache/*' > /dev/null 2>&1")
    
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
    expires = now + (730 * 24 * 60 * 60 * 1000000)
    
    sql = f"""
    DELETE FROM cookies WHERE host_key LIKE '%roblox.com' AND name='.ROBLOSECURITY';
    INSERT INTO cookies (creation_utc, top_frame_site_key, host_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, is_same_party) 
    VALUES ({now}, '', '.roblox.com', '.ROBLOSECURITY', '{safe_cookie}', '', '/', {expires}, 1, 1, {now}, 1, 1, 1, -1, 1, 443, 0);
    INSERT INTO cookies (creation_utc, top_frame_site_key, host_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, is_same_party) 
    VALUES ({now}, '', 'www.roblox.com', '.ROBLOSECURITY', '{safe_cookie}', '', '/', {expires}, 1, 1, {now}, 1, 1, 1, -1, 1, 443, 0);
    """
    
    tmp_sql = f"{CONFIG_DIR}/inject_{clone_id}.sql"
    with open(tmp_sql, "w") as f: f.write(sql)
    os.system(f"su -c 'cp {tmp_sql} /data/local/tmp/inject_{clone_id}.sql && chmod 644 /data/local/tmp/inject_{clone_id}.sql' > /dev/null 2>&1")
    os.system(f"su -c '{SQLITE_BIN} {cookies_db} < /data/local/tmp/inject_{clone_id}.sql' > /dev/null 2>&1")
    
    app_uid = os.popen(f"su -c 'stat -c %u {data_dir}' 2>/dev/null").read().strip()
    if app_uid:
        os.system(f"su -c 'chown -R {app_uid}:{app_uid} {data_dir} && chmod -R 777 {xml_dir}' > /dev/null 2>&1")
    os.system(f"su -c 'rm -f /data/local/tmp/inject_{clone_id}.sql && rm -f {tmp_sql}' > /dev/null 2>&1")
    
