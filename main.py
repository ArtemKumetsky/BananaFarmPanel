import json
import pyautogui
import time
import subprocess
from steam.guard import SteamAuthenticator


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


def get_steam_guard_code(mafile_path):
    with open(mafile_path, 'r') as f:
        mafile = json.load(f)

    authenticator = SteamAuthenticator(mafile)
    return authenticator.get_code()


def login_and_launch_game(account):
    print(f"Launching {account['login']}")
    # get SDA code
    auth_code = get_steam_guard_code(account["mafile_path"])

    # Launch steam
    subprocess.Popen([steam_path])
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
    pyautogui.locateOnScreen("assets/login/steam_logged_in.png", 300)
    print(f"{account['login']}: Logged into account!")

    # Запуск игры
    subprocess.Popen([steam_path, "-applaunch", game_id])
    pyautogui.locateOnScreen("assets/game_launched.png", 300)
    print(f"{account['login']}: Game launched!")


    # close steam
    # subprocess.call("taskkill /f /im steam.exe", shell=True)


def logout_from_account():
    # Находим и нажимаем на кнопку Steam в верхнем левом углу
    logout_steam_menu = pyautogui.locateCenterOnScreen('assets/steam_menu.png')
    pyautogui.click(logout_steam_menu, duration=0.5)

    # Пауза перед нажатием клавиши "Выйти"
    time.sleep(2)

    # Находим и нажимаем на кнопку "Выйти"
    logout_button_location = pyautogui.locateOnScreen('assets/steam_logout_btn.png')
    if logout_button_location is not None:
        logout_button_x, logout_button_y = pyautogui.center(logout_button_location)
        pyautogui.click(logout_button_x, logout_button_y, duration=0.5)
        print("Успешно вышли из аккаунта.")
    else:
        print("Ошибка: Не удалось найти кнопку 'Выйти из аккаунта'.")

# main cycle
for account in accounts:
    login_and_launch_game(account)
    time.sleep(5)
    # logout_from_account()


#compile
# pyinstaller main.py --onefile