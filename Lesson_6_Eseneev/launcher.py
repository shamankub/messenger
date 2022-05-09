import subprocess


PROCESS = []

while True:
    ANSWER = input(
        "Выберите действие: q - выход, s - запустить сервер и клиенты, x - закрыть все окна: "
    )

    if ANSWER == "q":
        break
    elif ANSWER == "s":
        run_path = "python Lesson_5_Eseneev/"
        PROCESS.append(subprocess.Popen(f"{run_path}server.py", shell=True))
        for i in range(5):
            PROCESS.append(subprocess.Popen(f"{run_path}client.py", shell=True))
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
