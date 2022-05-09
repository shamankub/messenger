import subprocess


def main():
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
        elif ANSWER == "k":
            print(
                "Убедитесь, что на сервере зарегистрировано необходимо количество клиентов с паролем 123456."
            )
            print("Первый запуск может быть достаточно долгим из-за генерации ключей!")
            COUNT = int(input("Введите количество тестовых клиентов для запуска: "))
            # Запускаем клиентов:
            for i in range(COUNT):
                PROCESS.append(
                    subprocess.Popen(
                        ["konsole", "-e", f"python client.py -n user{i+1} -p 123456"]
                    )
                )
        elif ANSWER == "x":
            while PROCESS:
                VICTIM = PROCESS.pop()
                VICTIM.kill()


if __name__ == "__main__":
    main()
