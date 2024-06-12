import json
import logging
import threading

import pyautogui
import time
import subprocess
from steam.guard import SteamAuthenticator

# logs creation
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

print(
    "Я слишком ленив, чтобы пилить сервер авторизации, потому просто знай - если ты это спиздил"
    " или где-то достал бесплатно, то хоть ключик какой-то мне закинь, не будь гнидой.")
print("Я тоже кушать хочу хоть иногда!")
print("TG: @jabablet")
print("А если купил, то целую в щёчку (без гейства)")
print("Вот теперь за работу!")


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


def get_steam_guard_code(mafile_path):
    with open(mafile_path, 'r') as f:
        mafile = json.load(f)

    authenticator = SteamAuthenticator(mafile)
    return authenticator.get_code()


def find(image_path, timeout):
    print("looking for some sheet...")
    try:
        location = pyautogui.locateOnScreen(image_path, timeout)
        if location is not None:
            pyautogui.click(pyautogui.center(location))
    except Exception as e:
        print(f"Sheet is not detected! {e}")


def delayed_kill(account):
    pid = process_ids.get(account['login'])
    print("Termination timer started, acc will be killed in " + str(terminate_timer) + " seconds")
    time.sleep(terminate_timer)
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
    print(f"{account['login']} termination done!")


def login_and_launch_game(account):
    print(f"Launching {account['login']}")
    # get SDA code
    auth_code = get_steam_guard_code(account["mafile_path"])

    # Launch steam
    steam_window = subprocess.Popen([steam_path, "-applaunch", game_id])
    process_ids[account['login']] = steam_window.pid
    pyautogui.locateOnScreen("assets/login/login_btn.png", 300)
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

    # check EULA
    find("assets/friends_window_close_btn.png", 10)
    time.sleep(1)
    find("assets/accept_eula.png", 3)

    # continue
    pyautogui.locateOnScreen("assets/login/steam_logged_in.png", 300)
    print(f"{account['login']}: Logged into account!")

    # Confirm cloud error
    time.sleep(2)
    pyautogui.press("enter")

    # close steam window
    time.sleep(2)
    pyautogui.click(pyautogui.locateCenterOnScreen("assets/close_steam_window.png"))

    # Check game launch
    pyautogui.locateOnScreen("assets/game_launched.png", 300)
    print(f"{account['login']}: Game launched!")

    pyautogui.click(pyautogui.locateCenterOnScreen("assets/minimize_game.png"))

    # close advert windows
    find("assets/avdert_close_btn.png", 3)
    find("assets/avdert_close_btn.png", 3)

    if terminate_timer > 0:
        # start terminate timer
        threading.Thread(target=delayed_kill, args=(account,)).start()

    # close steam
    # subprocess.call("taskkill /f /im gameoverlayui.exe", True)
    # print(f"{account['login']}: Game overlay closed!")


while True:
    for account in accounts:
        try:
            login_and_launch_game(account)
            counter = counter + 1
            print("\naccounts launched: " + str(counter))
            time.sleep(3)
        except Exception as e:
            logging.error(f"Error in main function: {e}")

# compile
# pyinstaller main.py --onefile
