import json
import logging
import os
import sys
import threading
import pyautogui
import time
import subprocess
from steam.guard import SteamAuthenticator
import uuid
import firebase_admin
from firebase_admin import credentials, firestore

# logs creation
logging.basicConfig(filename='panel.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


# Получение пути к директории, где находится исполняемый файл
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Инициализация Firebase
cred = credentials.Certificate(resource_path("SDK/bananapanel-firebase-adminsdk.json"))
firebase_admin.initialize_app(cred)
db = firestore.client()


def getHWID():
    hwid = hex(uuid.getnode())
    return hwid


def is_hwid_allowed(hwid):
    doc_ref = db.collection('allowed_hwids').document(hwid)
    doc = doc_ref.get()
    return doc.exists


def checkHWID():
    hwid = getHWID()
    if is_hwid_allowed(hwid):
        print("HWID successfully checked! Launching program...")
    else:
        print("Error: HWID is unregistered. Please contact TG @jabablet !")
        print("Your current HWID: " + hwid)
        time.sleep(30)
        exit(1)


checkHWID()


# read accounts data from logpass.txt and add them to temporary array
def read_accounts(file_path):
    accounts = []
    with open(file_path, 'r') as f:
        for line in f:
            login, password = line.strip().split(':')
            accounts.append({"login": login, "password": password})

    return accounts


accounts = read_accounts('logpass.txt')

# get mafiles
for account in accounts:
    account["mafile_path"] = f"mafiles/{account['login']}.mafile"

# Steam path
with open('settings.json', 'r') as f:
    config = json.load(f)

steam_path = config['steam_path']
game_id = "2923300"
global steam_window, counter, terminate_timer, process_ids
process_ids = {}
counter: int = 0
terminate_timer = config['terminate_timer']
steam_launch_attributes = config['steam_launch_attributes']


def get_steam_guard_code(mafile_path):
    with open(mafile_path, 'r') as f:
        mafile = json.load(f)

    authenticator = SteamAuthenticator(mafile)
    return authenticator.get_code()


def find(image_path, timeout):
    print(f"looking for {image_path}...")
    try:
        location = pyautogui.locateOnScreen(image_path, timeout)
        if location is not None:
            pyautogui.click(pyautogui.center(location))
            print(f"{image_path} found! Closing...")
    except Exception as e:
        print(f"{image_path} not detected! {e}")


def delayed_kill(pid,login):
    print("Termination timer started, acc will be killed in " + str(terminate_timer) + " seconds")
    time.sleep(terminate_timer)
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
    print(f"{login} termination done!")


def login_and_launch_game(account):
    try:
        print(f"Launching {account['login']}")
        # get SDA code
        auth_code = get_steam_guard_code(account["mafile_path"])

        # Launch steam
        steam_window = subprocess.Popen([steam_path, "-applaunch", game_id] + steam_launch_attributes)
        process_ids[account['login']] = steam_window.pid

        # wait till steam launched
        pyautogui.locateOnScreen("assets/login/steam_launched.png", 300)
        print(f"{account['login']}: Steam launched!")

        # enter login
        pyautogui.write(account["login"])
        pyautogui.press("tab")

        # enter password
        pyautogui.write(account["password"])
        pyautogui.press("enter")
        pyautogui.locateOnScreen("assets/login/sda_request.png", 300)

        # enter SDA code
        pyautogui.write(auth_code)
        pyautogui.press("enter")

        # check game ban notification
        find("assets/notifications/game_ban_window_close.png", 10)

        # check EULA
        find("assets/notifications/accept_eula.png", 10)

        # continue
        pyautogui.locateOnScreen("assets/login/steam_logged_in.png", 300)
        print(f"{account['login']}: Logged into account!")

        # check cloud sync fail notification
        find("assets/notifications/sync_failed.png", 5)

        # close steam window
        find("assets/close_steam_window.png", 30)

        # Check game launch
        pyautogui.locateOnScreen("assets/game_launched.png", 300)
        print(f"{account['login']}: Game launched!")

        # minimize game
        find("assets/minimize_game.png", 300)

        # start terminate timer if it enabled in settings.json
        if terminate_timer > 0:
            threading.Thread(target=delayed_kill, args=(steam_window.pid, account['login'])).start()
    except Exception as e:
        logging.error(f"Error in main function: {e}")


while True:
    for account in accounts:
        try:
            login_and_launch_game(account)
            counter = counter + 1
            print("\naccounts launched: " + str(counter))
            time.sleep(3)
        except Exception as e:
            logging.error(f"Error in main cycle: {e}")

# compile
# pyinstaller --onefile --name BananaPanel --add-data "SDK/bananapanel-firebase-adminsdk.json;SDK" main.py
