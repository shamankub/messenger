import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), ".."))
from local.settings import ACCOUNT_NAME, ACTION, ERROR, PRESENCE, RESPONSE, TIME, USER
from server import process_client_message


class TestServer(unittest.TestCase):

    err_dict = {RESPONSE: 400, ERROR: "Bad Request"}
    ok_dict = {RESPONSE: 200}

    def test_no_action(self):
        """Ошибка, если нет действия."""
        self.assertEqual(
            process_client_message({TIME: "1.1", USER: {ACCOUNT_NAME: "Guest"}}),
            self.err_dict,
        )

    def test_wrong_action(self):
        """Ошибка, если неизвестное действие."""
        self.assertEqual(
            process_client_message({ACTION: "Wrong", TIME: "1.1", USER: {ACCOUNT_NAME: "Guest"}}),
            self.err_dict,
        )

    def test_no_time(self):
        """Ошибка, если  запрос не содержит штампа времени."""
        self.assertEqual(
            process_client_message({ACTION: PRESENCE, USER: {ACCOUNT_NAME: "Guest"}}),
            self.err_dict,
        )

    def test_no_user(self):
        """Ошибка, если нет пользователя."""
        self.assertEqual(process_client_message({ACTION: PRESENCE, TIME: "1.1"}), self.err_dict)

    def test_unknown_user(self):
        """Ошибка, если пользователь не Guest."""
        self.assertEqual(
            process_client_message({ACTION: PRESENCE, TIME: "1.1", USER: {ACCOUNT_NAME: "User"}}),
            self.err_dict,
        )

    def test_ok_check(self):
        """Корректный запрос."""
        self.assertEqual(
            process_client_message({ACTION: PRESENCE, TIME: "1.1", USER: {ACCOUNT_NAME: "Guest"}}),
            self.ok_dict,
        )


if __name__ == "__main__":
    unittest.main()
