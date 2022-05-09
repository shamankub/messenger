import inspect
import logging
import sys

import project_log.configs.client_logger
import project_log.configs.server_logger

# Ищем client в аргументах командной строки
# Если client не найден, то server
if sys.argv[0].find("client") == -1:
    LOG = logging.getLogger("server")
else:
    LOG = logging.getLogger("client")

# Декоратор
def log(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        LOG.debug(
            f"Была вызвана функция {func.__name__} c параметрами {args}, {kwargs}. "
            f"Вызов из модуля {func.__module__}. "
            f"Вызов из функции {inspect.stack()[1][3]}.",
            stacklevel=2,
        )
        return res

    return wrapper
