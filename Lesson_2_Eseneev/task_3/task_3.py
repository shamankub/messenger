"""
3. Задание на закрепление знаний по модулю yaml.
 Написать скрипт, автоматизирующий сохранение данных
 в файле YAML-формата.
Для этого:

Подготовить данные для записи в виде словаря, в котором
первому ключу соответствует список, второму — целое число,
третьему — вложенный словарь, где значение каждого ключа —
это целое число с юникод-символом, отсутствующим в кодировке
ASCII(например, €);

Реализовать сохранение данных в файл формата YAML — например,
в файл file.yaml. При этом обеспечить стилизацию файла с помощью
параметра default_flow_style, а также установить возможность работы
с юникодом: allow_unicode = True;

Реализовать считывание данных из созданного файла и проверить,
совпадают ли они с исходными.
"""

import yaml


dict_w = {
    "items": ["computer", "keyboard", "mouse", "printer"],
    "items_quantity": 4,
    "items_price": {
        "computer": "15000\u20bd-70000\u20bd",
        "keyboard": "70\u20aa-300\u20aa",
        "mouse": "100\u20bb-200\u20bb",
        "printer": "50\u20a4-600\u20a4",
    },
}


with open("./task_3/file.yaml", "w", encoding="utf-8") as f:
    yaml.dump(dict_w, f, default_flow_style=False, allow_unicode=True)

with open("./task_3/file.yaml", "r", encoding="utf-8") as f:
    dict_r = yaml.load(f, Loader=yaml.FullLoader)

print(f"Файл совпадает с исходным: {dict_w == dict_r}")
