"""
Задание 5.

Выполнить пинг веб-ресурсов yandex.ru, youtube.com и
преобразовать результаты из байтовового в строковый тип на кириллице.

Подсказки:
--- используйте модуль chardet, иначе задание не засчитается!!!
"""

import subprocess
from chardet import detect


def resource_ping(resource):
    args = ["ping", resource]
    res = subprocess.Popen(args, stdout=subprocess.PIPE)
    for line in res.stdout:
        result = detect(line)
        print(line.decode(result["encoding"]))


resource_ping("youtube.com")
resource_ping("yandex.ru")


"""
Не смог проверить работу кода на практике, потому что у меня терминал Ubuntu возвращает данные в ASCII:
PING yandex.ru (5.255.255.80) 56(84) bytes of data.
64 bytes from yandex.ru (5.255.255.80): icmp_seq=1 ttl=54 time=31.9 ms
64 bytes from yandex.ru (5.255.255.80): icmp_seq=2 ttl=54 time=31.0 ms
64 bytes from yandex.ru (5.255.255.80): icmp_seq=3 ttl=54 time=32.5 ms

Надеюсь, что всё работает. 
"""
