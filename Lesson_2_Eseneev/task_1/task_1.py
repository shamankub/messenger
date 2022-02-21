"""
1. Задание на закрепление знаний по модулю CSV. Написать скрипт,
осуществляющий выборку определенных данных из файлов info_1.txt, info_2.txt,
info_3.txt и формирующий новый «отчетный» файл в формате CSV.

Для этого:

Создать функцию get_data(), в которой в цикле осуществляется перебор файлов
с данными, их открытие и считывание данных. В этой функции из считанных данных
необходимо с помощью регулярных выражений извлечь значения параметров
«Изготовитель системы», «Название ОС», «Код продукта», «Тип системы».
Значения каждого параметра поместить в соответствующий список. Должно
получиться четыре списка — например, os_prod_list, os_name_list,
os_code_list, os_type_list. В этой же функции создать главный список
для хранения данных отчета — например, main_data — и поместить в него
названия столбцов отчета в виде списка: «Изготовитель системы»,
«Название ОС», «Код продукта», «Тип системы». Значения для этих
столбцов также оформить в виде списка и поместить в файл main_data
(также для каждого файла);

Создать функцию write_to_csv(), в которую передавать ссылку на CSV-файл.
В этой функции реализовать получение данных через вызов функции get_data(),
а также сохранение подготовленных данных в соответствующий CSV-файл;

Пример того, что должно получиться:

Изготовитель системы,Название ОС,Код продукта,Тип системы

1,LENOVO,Windows 7,00971-OEM-1982661-00231,x64-based

2,ACER,Windows 10,00971-OEM-1982661-00231,x64-based

3,DELL,Windows 8.1,00971-OEM-1982661-00231,x86-based

Обязательно проверьте, что у вас получается примерно то же самое.

ПРОШУ ВАС НЕ УДАЛЯТЬ СЛУЖЕБНЫЕ ФАЙЛЫ TXT И ИТОГОВЫЙ ФАЙЛ CSV!!!
"""


import re
import csv


def get_data():
    os_prod_list = []
    os_name_list = []
    os_code_list = []
    os_type_list = []
    main_data = [
        ["ID", "Изготовитель системы", "Название ОС", "Код продукта", "Тип системы"],
    ]

    for i in range(1, 4):
        with open(f"./task_1/info_{i}.txt", "r", encoding="utf-8") as f:
            text = f.read()

        def parce(reg):
            str = " ".join(re.compile(reg).findall(text)[0].split()[2:])
            return str

        os_prod = parce(r"Изготовитель системы:[^\n]*")
        os_prod_list.append(os_prod)
        os_name = parce(r"Название ОС:[^\n]*")
        os_name_list.append(os_name)
        os_code = parce(r"Код продукта:[^\n]*")
        os_code_list.append(os_code)
        os_type = parce(r"Тип системы:[^\n]*")
        os_type_list.append(os_type)

    for i in range(0, 3):
        row = []
        row.append(i + 1)
        row.append(os_prod_list[i])
        row.append(os_name_list[i])
        row.append(os_code_list[i])
        row.append(os_type_list[i])
        main_data.append(row)

    return main_data


def write_to_csv(file):
    with open(file, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(get_data())


write_to_csv("./task_1/get_data.csv")
