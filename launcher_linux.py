import subprocess
import time

PROCESS = []
# run_path = "temp/"
run_path = "Lesson_14_Eseneev/"

while True:
    ANSWER = input(
        "Выберите действие: q - выход, s - запустить сервер, k - запустить клиенты, x - закрыть все окна: "
    )
    if ANSWER == "q":
        break
    elif ANSWER == "s":
        # Запускаем сервер:
        PROCESS.append(
            subprocess.Popen(["konsole", "-e", f"python {run_path}server.py"])
        )
        time.sleep(0.5)
    elif ANSWER == "k":
        COUNT = int(input("Введите количество тестовых клиентов для запуска: "))
        # Запускаем клиентов:
        for i in range(COUNT):
            PROCESS.append(
                subprocess.Popen(
                    [
                        "konsole",
                        "-e",
                        f"python {run_path}client.py -n user{i + 1} -p 123456",
                    ]
                )
            )
            time.sleep(0.1)
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
