import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), ".."))
from client import create_presence, process_answer
from local.settings import ACCOUNT_NAME, ACTION, ERROR, PRESENCE, RESPONSE, TIME, USER


class TestClient(unittest.TestCase):
    def test_def_presense(self):
        """Тест корректного запроса."""
        test = create_presence("Guest")
        test[TIME] = "1.1"
        self.assertEqual(test, {ACTION: PRESENCE, TIME: "1.1", USER: {ACCOUNT_NAME: "Guest"}})

    def test_200_ans(self):
        """Тест корректного разбора ответа 200."""
        self.assertEqual(process_answer({RESPONSE: 200}), "200 : OK")

    def test_400_ans(self):
        """Тест корректного разбора ответа 400."""
        self.assertEqual(process_answer({RESPONSE: 400, ERROR: "Bad Request"}), "400 : Bad Request")

    def test_no_response(self):
        """Тест исключения без поля RESPONSE."""
        self.assertRaises(ValueError, process_answer, {ERROR: "Bad Request"})


if __name__ == "__main__":
    unittest.main()
