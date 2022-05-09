import subprocess
import time

PROCESS = []

while True:
    ANSWER = input(
        "Выберите действие: q - выход, s - запустить сервер и клиенты, x - закрыть все окна: "
    )
    COUNT = input("Введите количество клиентов: ")
    if ANSWER == "q":
        break
    elif ANSWER == "s":
        PROCESS.append(subprocess.Popen(["konsole", "-e", "python server.py"]))
        time.sleep(0.5)
        for i in range(int(COUNT)):
            PROCESS.append(
                subprocess.Popen(["konsole", "-e", f"python client.py -n user{i+1}"])
            )
            time.sleep(0.1)
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
    