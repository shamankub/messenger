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
        run_path = "python Lesson_8_Eseneev/"
        PROCESS.append(subprocess.Popen(["konsole", "-e", f"{run_path}server.py"]))
        time.sleep(0.1)
        for i in range(int(COUNT)):
            PROCESS.append(
                subprocess.Popen(["konsole", "-e", f"{run_path}client.py -n user{i+1}"])
            )
            time.sleep(0.1)
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
