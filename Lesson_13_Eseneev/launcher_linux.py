import subprocess
import time

PROCESS = []

while True:
    ANSWER = input(
        "Выберите действие: q - выход, s - запустить сервер, k - запустить клиенты, x - закрыть все окна: "
    )
    if ANSWER == "q":
        break
    elif ANSWER == "s":
        # Запускаем сервер:
        PROCESS.append(subprocess.Popen(["konsole", "-e", "python server.py"]))
        time.sleep(0.5)
    elif ANSWER == "k":
        COUNT = int(input("Введите количество тестовых клиентов для запуска: "))
        # Запускаем клиентов:
        for i in range(COUNT):
            PROCESS.append(
                subprocess.Popen(["konsole", "-e", f"python client.py -n user{i+1}"])
            )
            time.sleep(0.1)
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
