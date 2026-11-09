repeat task.wait() until game:IsLoaded()
getgenv().AA_CONFIG = {

    ------------------------------------------------------------
    -- ★ เลือกโหมด
    ------------------------------------------------------------
    -- 1 = ฟาร์มเพชร   : ไต่ด่าน Act 1-6 ไปเรื่อยๆ แล้วฟาร์ม Infinite ยาว
    -- 2 = ฟาร์มอีเวนต์ : ลง Summer Hunt กับคนอื่น (ได้ SummerPearls)
    -- 3 = ลงดัน       : ใช้ Dungeon Run Key ลงดันวนไป (ไม่มีคีย์ = เล่นด่านปกติรอ)
    Mode = 1,

    ------------------------------------------------------------
    -- ★ Auto DONE (ให้ตัวรีจอยสลับไอดี — Horst / Masterp / Storm)
    ------------------------------------------------------------
    AUTO_DONE = true,      -- true = เปิด / false = ปิด
    DONE_LEVEL = 40,        -- เลเวลถึงเท่านี้แล้ว DONE
    DONE_GEMS = 0,          -- เพชรถึงเท่านี้แล้ว DONE  เช่น 50000

    ------------------------------------------------------------
    -- ★ โหมด 1: ฟาร์มเพชร
    ------------------------------------------------------------
    LAST_WORLD = "aot",             -- ไต่ด่านถึงโลกนี้แล้วหยุด
                                    --   "namek" = Planet Greenie, "aot" = Walled City
    FINAL_FARM = "namek_infinite",  -- ไต่ครบแล้วฟาร์มด่านนี้ยาว
    HARD_CLIMB = false,              -- ไต่ระดับ Hard ด้วย (true / false)

    -- ด่าน Infinite: ถึงเวฟนี้ขายตัวทิ้งทั้งหมด ให้แพ้ไวแล้วเริ่มรอบใหม่ (เก็บเพชรไว)
    INF_SELL_WAVE = 0,      -- 0 = ไม่ขาย เล่นจนแพ้เอง  เช่น 15

    -- เล่นด่านเดียววนไปเรื่อยๆ ("" = ไต่ด่านปกติ)
    -- รายชื่อด่าน (เลขท้าย 1-6 = Act 1-6):
    --   Planet Greenie : "namek_level_1" ถึง "namek_level_6"
    --                    "namek_infinite"  = Infinite
    --   Walled City    : "aot_level_1" ถึง "aot_level_6"
    --   Snowy Town     : "demonslayer_level_1" ถึง "demonslayer_level_6"
    --   Sand Village   : "naruto_level_1" ถึง "naruto_level_6"
    --   Navy Bay       : "marineford_level_1" ถึง "marineford_level_6"
    --   Fiend City     : "tokyoghoul_level_1" ถึง "tokyoghoul_level_6"
    STAGE = "",
    STAGE_DIFF = "Normal",  -- "Normal" / "Hard"

    ------------------------------------------------------------
    -- ★ โหมด 2: อีเวนต์ Summer Hunt
    ------------------------------------------------------------
    Event = {
        Matchmaking = false,     -- true = ลงกับคนอื่น (กรอก Captcha เอง) / false = ลงคนเดียว
        Card = "coins",         -- การ์ด: "coins" เน้นเหรียญ / "safe" เน้นรอด
        NoCurseWave = 0,        -- ถึงเวฟนี้เลิกรับการ์ดคำสาป (0 = รับตลอด)  เช่น 20

        Coins = "summon",       -- "summon" = สุ่มตู้ Icy Star Capsule เอง / "keep" = เก็บ Pearls ไว้
        CoinsSummonAt = 10000,   -- Pearls ถึงเท่านี้แล้วกลับไปสุ่ม (1500 = สุ่ม x10)
    },

    ------------------------------------------------------------
    -- ★ ตั้งค่า (true = เปิด / false = ปิด)
    ------------------------------------------------------------
    Settings = {
        autoPlace = true,       -- วางตัว
        autoUpgrade = true,     -- อัปตัว
        autoSkip = true,        -- ข้ามเวฟ
        autoReplay = true,      -- จบรอบเล่นต่อ
        autoSummon = true,      -- สุ่มตัว
        codes = false,           -- ใส่โค้ด
        whiteScreen = false,    -- จอขาว (ลดเครื่องร้อน)
    },
}

loadstring(game:HttpGet("https://hamsterdiwa.com/loader/animeadv"))()
