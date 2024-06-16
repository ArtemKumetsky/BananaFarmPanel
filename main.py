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
from colorama import init, Fore, Style
from steam.client import SteamClient
from pysteamsignin.steamsignin import SteamSignIn

# Инициализация colorama
init()

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


def product_key_check():
    product_key = input("If you have a product key, please enter it: ").strip()
    doc_ref = db.collection('product_keys').document(product_key)
    doc = doc_ref.get()
    if doc.exists:
        print("Product key is valid! Saving your HWID to allowed list...")
        db.collection('allowed_hwids').document(getHWID()).set({product_key: True})
        db.collection('product_keys').document(product_key).delete()
    else:
        print("Wrong product key!")


def checkHWID():
    hwid = getHWID()
    if is_hwid_allowed(hwid):
        print("HWID successfully checked! Launching program...")
    else:

        print("Error: HWID is unregistered. Please contact TG @jabablet !")
        print("Your current HWID: " + hwid)
        product_key_check()
        time.sleep(30)
        exit(1)


checkHWID()


# read accounts data from logpass.txt and add them to temporary array
def read_accounts(file_path):
    try:
        accounts = []
        with open(file_path, 'r') as f:
            for line in f:
                login, password = line.strip().split(':')
                accounts.append({"login": login, "password": password})

        return accounts
    except Exception as e:
        print("Check your logpass.txt! Error:" + str(e))
        logging.error("Check your logpass.txt! Error:" + str(e))
        time.sleep(60)


accounts = read_accounts('logpass.txt')

# get mafiles
for account in accounts:
    try:
        account["mafile_path"] = f"mafiles/{account['login']}.mafile"
    except Exception as e:
        print("Check your mafiles! It will be renamed to accountLogin.mafile! Error: " + str(e))
        logging.error("Check your mafiles! It will be renamed to accountLogin.mafile! Error: " + str(e))
        time.sleep(60)


def get_steam_guard_code(mafile_path):
    with open(mafile_path, 'r') as f:
        mafile = json.load(f)

    authenticator = SteamAuthenticator(mafile)
    return authenticator.get_code()


# Parse settings.json
with open('settings.json', 'r') as f:
    config = json.load(f)

# init variables
steam_path = config['steam_path']
game_id = "2923300"
global steam_window, steam_launch_error
process_ids = {}
counter: int = 0
terminate_timer = config['terminate_timer']
steam_launch_attributes = config['steam_launch_attributes']


def find(image_path, timeout, action):
    global steam_launch_error
    print(Fore.YELLOW + f"looking for {image_path}...")
    try:
        location = pyautogui.locateOnScreen(image_path, timeout)
        if location is not None and action == 1:
            pyautogui.click(pyautogui.center(location))
            print(Fore.GREEN + f"{image_path} found! Closing...")
        if location is not None and action == 0:
            pyautogui.center(location)
            print(Fore.GREEN + f"{image_path} found!")
            if image_path == "assets/login/steam_launched.png":
                steam_launch_error = 0
                return steam_launch_error
    except Exception as e:
        print(Fore.RED + f"{image_path} not detected! {e}")
        # if steam not launched, kill previous window and open a new one
        if image_path == "assets/login/steam_launched.png":
            steam_launch_error = 1
            return steam_launch_error


def delayed_kill(pid, login, timer):
    print("Termination timer started, acc will be killed in " + str(timer) + " seconds\n")
    time.sleep(timer)
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=True)
    print(Fore.YELLOW + f"{login} termination done!")


def launch_steam(account):
    try:
        global steam_launch_error, steam_window
        steam_window = subprocess.Popen([steam_path] + steam_launch_attributes + ["-applaunch", game_id])
        process_ids[account['login']] = steam_window.pid
    except Exception as e:
        print("Error launching steam: " + str(e))


    # wait till steam launched
    steam_launch_error = find("assets/login/steam_launched.png", 30, 0)
    while steam_launch_error == 1:
        print(Fore.RED + "STEAM LAUNCHING ERROR! STEAM WILL BE RESTARTED.")
        threading.Thread(target=delayed_kill, args=(steam_window.pid, account['login'], 1)).start()
        time.sleep(5)
        print(Fore.GREEN + f"Launching {account['login']}")
        steam_window = subprocess.Popen([steam_path] + steam_launch_attributes + ["-applaunch", game_id])
        process_ids[account['login']] = steam_window.pid
        steam_launch_error = find("assets/login/steam_launched.png", 30, 0)
    return steam_window.pid


def login_and_launch_game(account):
    try:
        global steam_window
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        print(Fore.GREEN + f"Launching {account['login']}")

        # get SDA code
        auth_code = get_steam_guard_code(account["mafile_path"])

        # launch steam
        launch_steam(account)

        # enter login
        pyautogui.write(account["login"])
        pyautogui.press("tab")

        # enter password
        pyautogui.write(account["password"])
        pyautogui.press("enter")
        find("assets/login/sda_request.png", 10, 0)

        # enter SDA code
        pyautogui.write(auth_code)
        pyautogui.press("enter")

        # look for game ban window and close it
        find("assets/notifications/game_ban_window_close.png", 5, 1)

        # look for EULA
        find("assets/notifications/accept_eula.png", 10, 1)

        # look for game minimize game icon
        find("assets/game/minimize_game.png", 15, 1)

        # close steam
        find("assets/login/steam_minimize.png", 5, 1)

        # start terminate timer if it enabled in settings.json
        if terminate_timer > 0:
            threading.Thread(target=delayed_kill, args=(steam_window.pid, account['login'], terminate_timer)).start()
    except Exception as e:
        logging.error(f"Error in main function: {e}")


# if terminate_timer == 0, steam will not close, so we shouldn`t launch 1 acc second time
if terminate_timer > 0:
    while True:
        for account in accounts:
            try:
                print(Fore.WHITE + "--------------------------------------------------------------------")
                login_and_launch_game(account)
                counter = counter + 1
                print(Fore.WHITE + "--------------------------------------------------------------------")
                print(Fore.LIGHTGREEN_EX + "accounts launched: " + str(counter))
            except Exception as e:
                logging.error(Fore.RED + f"Error in main cycle: {e}")
else:
    for account in accounts:
        try:
            print(Fore.WHITE + "--------------------------------------------------------------------")
            login_and_launch_game(account)
            counter = counter + 1
            print(Fore.WHITE + "--------------------------------------------------------------------")
            print(Fore.LIGHTGREEN_EX + "accounts launched: " + str(counter))
        except Exception as e:
            logging.error(Fore.RED + f"Error in main cycle: {e}")
# compile
# pyinstaller --onefile --name BananaPanel --add-data "SDK/bananapanel-firebase-adminsdk.json;SDK" main.py
