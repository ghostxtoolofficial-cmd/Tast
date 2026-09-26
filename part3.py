def verify_license():
    LICENSE_FILE = os.path.join(CONFIG_DIR, "license.key")
    if not os.path.exists(LICENSE_FILE):
        print("\n\033[91m[!] Error: ไม่พบไฟล์ license.key กรุณารันระบบผ่าน start.sh\033[0m")
        sys.exit(1)
    with open(LICENSE_FILE, "r") as f: user_key = f.read().strip()
    client = PWFLicense()
    result = client.login(user_key)
    if not result.get("success"):
        os.remove(LICENSE_FILE)
        print("\n\033[91m[!] Error: License Key ของคุณหมดอายุ หรือไม่ถูกต้อง!\033[0m")
        sys.exit(1)
    def on_revoked(code, message): os._exit(0)
    threading.Thread(target=client.run_heartbeat, args=(on_revoked,), daemon=True).start()
    return True
    
