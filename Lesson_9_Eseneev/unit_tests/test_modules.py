import json
import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), ".."))
from local.modules import get_message, send_message
from local.settings import ACCOUNT_NAME, ACTION, ERROR, PRESENCE, RESPONSE, TIME, USER


class TestSocket:
    """
    Тестовый класс для тестирования отправки и получения, при создании требует словарь, который
    будет прогоняться через тестовую функцию.
    """

    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        """
        Тестовая функция отправки, корректно  кодирует сообщение, также сохраняет что должно быть
        отправлено в сокет. message_to_send - то, что отправляем в сокет.
        """
        json_test_message = json.dumps(self.test_dict)
        # Кодирует сообщение.
        self.encoded_message = json_test_message.encode("utf-8")
        # Сохраняем что должно быть отправлено в сокет.
        self.received_message = message_to_send

    def recv(self, max_len):
        """Получаем данные из сокета."""
        json_test_message = json.dumps(self.test_dict)
        return json_test_message.encode("utf-8")


class TestModules(unittest.TestCase):

    test_dict_send = {
        ACTION: PRESENCE,
        TIME: "1.1",
        USER: {ACCOUNT_NAME: "test_test"},
    }
    test_dict_recv_ok = {RESPONSE: 200}
    test_dict_recv_err = {RESPONSE: 400, ERROR: "Bad Request"}

    def test_send_message(self):
        """
        Тестируем корректность работы функции отправки, создадим тестовый сокет и проверим
        корректность отправки словаря.
        """
        # Экземпляр тестового словаря. Хранит собственно тестовый словарь.
        test_socket = TestSocket(self.test_dict_send)
        # Вызов тестируемой функции. Результаты будут сохранены в тестовом сокете.
        send_message(test_socket, self.test_dict_send)
        # Проверка корректности кодирования словаря.
        # Сравниваем результат доверенного кодирования и результат от тестируемой функции.
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)
        # Дополнительно проверим генерацию исключения при не словаре на входе.
        with self.assertRaises(Exception):
            send_message(test_socket, test_socket)

    def test_get_message(self):
        """Тест функции приёма сообщения."""
        test_sock_ok = TestSocket(self.test_dict_recv_ok)
        test_sock_err = TestSocket(self.test_dict_recv_err)
        # Тест корректной расшифровки корректного словаря.
        self.assertEqual(get_message(test_sock_ok), self.test_dict_recv_ok)
        # Тест корректной расшифровки ошибочного словаря.
        self.assertEqual(get_message(test_sock_err), self.test_dict_recv_err)


if __name__ == "__main__":
    unittest.main()
