import dis

# Метакласс, выполняющий базовую проверку класса "Server":
class ServerVerifier(type):
    def __init__(self, clsname, bases, clsdict):

        # Список методов, которые используются в функциях класса:
        methods = []

        # Атрибуты, используемые в функциях классов
        attrs = []

        # Перебираем ключи
        for func in clsdict:
            try:
                # Возвращает итератор по инструкциям в предоставленной функции, методе,
                # строке исходного кода или объекте кода.
                ret = dis.get_instructions(clsdict[func])
                # Если не функция то ловим исключение
            except TypeError:
                pass
            else:
                # Если функция - разбираем код, получая используемые методы и атрибуты.
                for el in ret:
                    if el.opname == "LOAD_GLOBAL":
                        if el.argval not in methods:
                            # Заполняем список методами, использующимися в функциях класса
                            methods.append(el.argval)
                    elif el.opname == "LOAD_ATTR":
                        if el.argval not in attrs:
                            # Заполняем список атрибутами, использующимися в функциях класса
                            attrs.append(el.argval)
        # Если обнаружено использование недопустимого метода "connect", бросаем исключение:
        if "connect" in methods:
            raise TypeError(
                "Использование метода connect недопустимо в серверном классе"
            )
        # Если сокет не инициализировался константами SOCK_STREAM(TCP), AF_INET(IPv4),
        # тоже исключение.
        if not ("SOCK_STREAM" in attrs and "AF_INET" in attrs):
            raise TypeError("Некорректная инициализация сокета.")
        # Обязательно вызываем конструктор предка:
        super().__init__(clsname, bases, clsdict)


# Метакласс, выполняющий базовую проверку класса "Client":
class ClientVerifier(type):
    def __init__(self, clsname, bases, clsdict):
        # Список методов, которые используются в функциях класса:
        methods = []
        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
                # Если не функция, то ловим исключение
            except TypeError:
                pass
            else:
                # Если функция - разбираем код, получая используемые методы.
                for el in ret:
                    if el.opname == "LOAD_GLOBAL":
                        if el.argval not in methods:
                            methods.append(el.argval)
        # Если обнаружено использование недопустимого метода "accept", "listen", "socket"
        # бросаем исключение:
        for command in ("accept", "listen", "socket"):
            if command in methods:
                raise TypeError(
                    "В классе обнаружено использование недопустимого метода"
                )
        # Вызов get_message или send_message из utils считаем корректным использованием сокетов
        if "get_message" in methods or "send_message" in methods:
            pass
        else:
            raise TypeError("Отсутствуют вызовы функций, работающих с сокетами.")
        super().__init__(clsname, bases, clsdict)
