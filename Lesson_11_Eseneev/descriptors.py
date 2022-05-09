import logging
import sys

# Ищем client в аргументах командной строки
# Если client не найден, то server
if sys.argv[0].find("client") == -1:
    LOG = logging.getLogger("server")
else:
    LOG = logging.getLogger("client")

# Дескриптор для описания порта:
class Port:
    def __set__(self, instance, listen_port):
        if not 1023 < listen_port < 65536:
            LOG.critical(
                f"Сервер остановлен. port: {listen_port} не входит в диапазон от 1024 до 65535."
            )
            exit(1)
        # Если порт прошел проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = listen_port

    def __set_name__(self, owner, name):
        self.name = name
