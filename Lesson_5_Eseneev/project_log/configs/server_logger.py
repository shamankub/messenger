import logging
import logging.handlers
import os
import sys

sys.path.append("../")


# Создаём объект форматирования:
FORMATTER = logging.Formatter("%(asctime)-30s %(levelname)-15s %(message)s")

# Создаём файл для логгирования:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, "../logs/server.log")

# Создаём потоковый обработчик логгирования:
STREAM_HANDLER = logging.StreamHandler(sys.stderr)
STREAM_HANDLER.setFormatter(FORMATTER)
STREAM_HANDLER.setLevel(logging.ERROR)

# Создаём файловый обработчик логгирования:
FILE_HANDLER = logging.handlers.TimedRotatingFileHandler(
    PATH, encoding="utf8", interval=1, when="D"
)
FILE_HANDLER.setFormatter(FORMATTER)

# Создаём объект-логгер с именем server:
LOG = logging.getLogger("server")

# Добавляем в логгер новый обработчик событий и устанавливаем уровень логгирования:
LOG.addHandler(STREAM_HANDLER)
LOG.addHandler(FILE_HANDLER)
LOG.setLevel(logging.DEBUG)

# Отладка в главной программе:
if __name__ == "__main__":
    LOG.critical("Критическая ошибка")
    LOG.error("Ошибка")
    LOG.info("Информационное сообщение")
    LOG.debug("Отладочная информация")
