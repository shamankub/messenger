Local package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт decorators.py
--------------------

.. automodule:: local.decorators
	:members:
	
Скрипт descriptors.py
---------------------

.. autoclass:: local.descriptors.Port
    :members:
   
Скрипт errors.py
----------------
   
.. autoclass:: local.errors.ServerError
   :members:
   
Скрипт metaclasses.py
---------------------

.. autoclass:: local.metaclasses.ServerMaker
   :members:
   
.. autoclass:: local.metaclasses.ClientMaker
   :members:
   
Скрипт modules.py
-----------------

local.modules. **get_message** (client)


	Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
	декодирует полученное сообщение и проверяет что получен словарь.

local.modules. **send_message** (sock, message)


	Функция отправки словарей через сокет. Кодирует словарь в формат JSON и отправляет через сокет.


Скрипт settings.py
------------------

Содержит разные глобальные переменные проекта.