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
        res = self.session.post(self.BASE_URL + endpoint, data=self.crypto.encrypt(body), timeout=15)
        return self._parse_reply(res)
    def login(self, license_key):
        result = self._post("/api/auth/login.php", {"license_key": license_key, "hwid": self.get_hwid()})
        if result.get("success"):
            self.session_id = result.get("session_id")
            self.license_key = license_key
            self.heartbeat_interval = int(result.get("heartbeat_interval", 30))
        return result
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

