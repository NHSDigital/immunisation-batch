import os
import io
import csv


def convert_csv_to_string(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        return "".join(file.readlines())


def convert_csv_to_reader(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        data = file.read()
    return csv.reader(io.StringIO(data), delimiter="|")


def convert_string_to_dict_reader(data_string: str):
    return csv.DictReader(io.StringIO(data_string), delimiter="|")
