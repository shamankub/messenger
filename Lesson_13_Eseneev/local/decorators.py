import logging
import sys

import logs.configs.client_logger
import logs.configs.server_logger

# метод определения модуля, источника запуска.
if sys.argv[0].find("client") == -1:
    # если не клиент то сервер!
    logger = logging.getLogger("server")
else:
    # ну, раз не сервер, то клиент
    logger = logging.getLogger("client")


def log(func_to_log):
    def log_saver(*args, **kwargs):
        logger.debug(
            f"Была вызвана функция {func_to_log.__name__} c параметрами {args} , {kwargs}. Вызов из модуля {func_to_log.__module__}"
        )
        ret = func_to_log(*args, **kwargs)
        return ret

    return log_saver
