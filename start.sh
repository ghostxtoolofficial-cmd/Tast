#!/bin/bash
CONFIG_DIR="/storage/emulated/0/Ghost X Tool Manager"
SWITCH_DIR="$CONFIG_DIR/AutoSwitch"
SETTING_FILE="$CONFIG_DIR/Setting.txt"
COOKIE_FILE="$CONFIG_DIR/cookie.txt"
LICENSE_FILE="$CONFIG_DIR/license.key"

GREEN="\e[32m"
RED="\e[31m"
CYAN="\e[36m"
WHITE="\e[97m"
YELLOW="\e[93m"
RESET="\e[0m"

mkdir -p "$CONFIG_DIR" 2>/dev/null
mkdir -p "$SWITCH_DIR" 2>/dev/null

# [NEW] ลบไฟล์เก่าที่เป็นต้นเหตุของ Error สีแดงทิ้ง
rm -f "$CONFIG_DIR/pwf_license.py" "$CONFIG_DIR/pwf_license.pyc" 2>/dev/null

if [ ! -f "$LICENSE_FILE" ]; then
    stty sane 2>/dev/null
    clear
    echo -e "${CYAN}========================================${RESET}"
    echo -e "${WHITE}           GHOST X HUB - AUTH           ${RESET}"
    echo -e "${CYAN}========================================${RESET}"
    read -p " [?] Enter License Key: " INPUT_KEY </dev/tty
    
    if [ -z "$INPUT_KEY" ]; then
        echo -e "\n${RED} [!] Key cannot be empty! Exiting...${RESET}"
        exit 1
    fi
    
    echo "$INPUT_KEY"> "$LICENSE_FILE"
    echo -e "${GREEN} [+] Key saved. Loading system...${RESET}"
    sleep 1
fi

clear
echo -e "${CYAN}========================================${RESET}"
echo -e "${WHITE}      INITIALIZING GHOST X SYSTEM       ${RESET}"
echo -e "${CYAN}========================================${RESET}"

sleep 1

if [ ! -f "$SETTING_FILE" ]; then
    echo "MODE=NORMAL" > "$SETTING_FILE"
    echo "MAP_ID=" >> "$SETTING_FILE"
    echo "MAX_CLONES=ALL" >> "$SETTING_FILE"
    echo "CHECK_INTERVAL=30" >> "$SETTING_FILE"
    echo "TIMEOUT=40" >> "$SETTING_FILE"
    echo "LAUNCH_DELAY=15" >> "$SETTING_FILE"
    echo "LOOP_DELAY=60" >> "$SETTING_FILE"
else
    if ! grep -q "^MAX_CLONES=" "$SETTING_FILE"; then
        sed -i '1iMAX_CLONES=ALL' "$SETTING_FILE"
    fi
fi

kill -9 $(lsof -t -i:5000) 2>/dev/null
su -c 'kill -9 $(lsof -t -i:5000)' 2>/dev/null
fuser -k -9 5000/tcp 2>/dev/null
pkill -9 -f python
killall -9 ssh 2>/dev/null
rm -f "$CONFIG_DIR/tunnel.log"

ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 serveo.net > "$CONFIG_DIR/tunnel.log" 2>&1 &

scan_apps() {
    MAX_C=$(grep "^MAX_CLONES=" "$SETTING_FILE" | cut -d'=' -f2)
    > "$CONFIG_DIR/apps.txt"
    
    if [[ "$MAX_C" =~ ^[0-9]+$ ]]; then
        su -c 'pm list packages' | grep -i roblox | cut -d':' -f2 | tr -d '\r' | tr -d ' ' | head -n "$MAX_C" > "$CONFIG_DIR/apps.txt"
    else
        su -c 'pm list packages' | grep -i roblox | cut -d':' -f2 | tr -d '\r' | tr -d ' ' > "$CONFIG_DIR/apps.txt"
    fi
    
    app_count=$(grep -c . "$CONFIG_DIR/apps.txt")
    if [ "$app_count" -eq 0 ]; then
        echo "com.roblox.client" > "$CONFIG_DIR/apps.txt"
    fi
}

if [ ! -f "$CONFIG_DIR/apps.txt" ]; then
    scan_apps
fi

# [NEW] เปลี่ยนมาเรียกเช็คคีย์ผ่าน main.py แทน
python -c "
import sys, os
try:
    sys.path.append('$CONFIG_DIR')
    from main import PWFLicense
    client = PWFLicense()
    with open('$LICENSE_FILE', 'r') as f:
        key = f.read().strip()
    res = client.login(key)
    if res.get('success'):
        print('ACTIVE')
    else:
        print('EXPIRED')
except Exception as e:
    print('ERROR')
" > "$CONFIG_DIR/key_status.txt" 2>/dev/null

stty sane 2>/dev/null

while true; do
    clear
    MODE_STATUS=$(grep "^MODE=" "$SETTING_FILE" | cut -d'=' -f2)
    MAP_ID=$(grep "^MAP_ID=" "$SETTING_FILE" | cut -d'=' -f2)
    MAX_CLONES=$(grep "^MAX_CLONES=" "$SETTING_FILE" | cut -d'=' -f2)
    
    KEY_STATUS=$(cat "$CONFIG_DIR/key_status.txt" 2>/dev/null | tr -d '\r\n')
    if [ -z "$KEY_STATUS" ]; then
        KEY_STATUS="ERROR"
    fi
    
    if [ "$KEY_STATUS" == "ACTIVE" ]; then
        STATUS_COLOR=$GREEN
    else
        STATUS_COLOR=$RED
    fi
    
    echo -e "${CYAN}========================================${RESET}"
    echo -e "${WHITE}          Ghost X Tool Manager          ${RESET}"
    echo -e "${CYAN}========================================${RESET}"
    echo -e " [System Mode] : ${WHITE}${MODE_STATUS}${RESET}"
    echo -e " [Max Screens] : ${WHITE}${MAX_CLONES}${RESET}"
    echo -e " [Target Map]  : ${WHITE}${MAP_ID:-None}${RESET}"
    echo -e " [Key Status]  : ${STATUS_COLOR}${KEY_STATUS}${RESET}"
    echo -e "${CYAN}========================================${RESET}"
    echo -e " [1] Start System"
    echo -e " [2] Rescan Roblox Apps"
    echo -e " [3] Set Target Map (Place ID)"
    echo -e " [4] Set Max Screens"
    echo -e " [5] Auto Cookie Normal"
    echo -e " [6] Edit Cookie Normal"
    echo -e " [7] Toggle Mode (Normal / Auto-Switch)"
    echo -e " [8] Kill All Roblox Apps"
    echo -e " [9] Exit"
    echo -e "${CYAN}========================================${RESET}"
    read -p " Select Option: " opt </dev/tty

    case $opt in
        1)
            if [ "$MODE_STATUS" == "AUTO_SWITCH" ]; then
                if [ ! -f "$SWITCH_DIR/clone_1.txt" ]; then
                    echo -e "\n${RED}[!] Missing AutoSwitch files.${RESET}"
                    sleep 2
                    continue
                fi
            fi
            
            clear
            cd "$CONFIG_DIR" || exit
            python -u main.py &
            PY_PID=$!
            
            echo -e "${CYAN}========================================${RESET}"
            echo -e "${GREEN}[+] SYSTEM IS RUNNING [${MODE_STATUS}]${RESET}"
            echo -e "${WHITE}[>] Press [ENTER] to stop the process.${RESET}"
            echo -e "${CYAN}========================================${RESET}\n"
            
            read -r </dev/tty
            
            kill -9 $PY_PID 2>/dev/null
            pkill -9 -f python 2>/dev/null
            sleep 1
            ;;
        2|3|4|5|6|7|8|9|0)
            if [ "$opt" == "9" ] || [ "$opt" == "0" ]; then clear; exit 0; fi
            if [ "$opt" == "2" ]; then scan_apps; sleep 1; fi
            if [ "$opt" == "3" ]; then read -p " Enter New Map ID: " in_map </dev/tty; sed -i "s/^MAP_ID=.*/MAP_ID=$in_map/" "$SETTING_FILE"; sleep 1; fi
            if [ "$opt" == "4" ]; then read -p " Enter max screens (Number or ALL): " in_clones </dev/tty; if [ -n "$in_clones" ]; then sed -i "s/^MAX_CLONES=.*/MAX_CLONES=$in_clones/" "$SETTING_FILE"; scan_apps; fi; sleep 1; fi
            if [ "$opt" == "5" ]; then app_count=$(grep -c . "$CONFIG_DIR/apps.txt"); > "$COOKIE_FILE"; for i in $(seq 1 $app_count); do pkg=$(sed -n "${i}p" "$CONFIG_DIR/apps.txt"); echo -e "\n${WHITE}[Clone $i : $pkg]${RESET}"; read -p " Paste Cookie: " cookie_data </dev/tty; echo "$cookie_data">> "$COOKIE_FILE"; done; sleep 2; fi
            if [ "$opt" == "6" ]; then nano "$COOKIE_FILE"; clear; sleep 1; fi
            if [ "$opt" == "7" ]; then if [ "$MODE_STATUS" == "NORMAL" ]; then sed -i "s/^MODE=.*/MODE=AUTO_SWITCH/" "$SETTING_FILE"; app_count=$(grep -c . "$CONFIG_DIR/apps.txt"); for i in $(seq 1 $app_count); do touch "$SWITCH_DIR/clone_${i}.txt"; done; else sed -i "s/^MODE=.*/MODE=NORMAL/" "$SETTING_FILE"; fi; sleep 1; fi
            if [ "$opt" == "8" ]; then if [ -f "$CONFIG_DIR/apps.txt" ]; then while IFS= read -r pkg; do if [ -n "$pkg" ]; then clean_pkg=$(echo "$pkg" | tr -d '\r' | tr -d ' '); su -c "am force-stop $clean_pkg" > /dev/null 2>&1; su -c "killall -9 $clean_pkg" > /dev/null 2>&1; fi; done < "$CONFIG_DIR/apps.txt"; fi; sleep 2; fi
            ;;
        *)
            sleep 1
            ;;
    esac
done
