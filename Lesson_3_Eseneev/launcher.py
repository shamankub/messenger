import subprocess


PROCESS = []

while True:
    ANSWER = input(
        "Выберите действие: q - выход, s - запустить сервер и клиенты, x - закрыть все окна: "
    )

    if ANSWER == "q":
        break
    elif ANSWER == "s":
        PROCESS.append(subprocess.Popen("python server.py", shell=True))
        for i in range(5):
            PROCESS.append(subprocess.Popen("python client.py", shell=True))
    elif ANSWER == "x":
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
