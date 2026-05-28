import os
import csv
import json
import xml.etree.ElementTree as ET

def parse_file(file_path):
    _, file_extension = os.path.splitext(file_path)
    
    if file_extension == ".txt":
        return parse_txt(file_path)
    elif file_extension == ".csv":
        return parse_csv(file_path)
    elif file_extension == ".json":
        return parse_json(file_path)
    elif file_extension == ".xml":
        return parse_xml(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def parse_txt(file_path):
    with open(file_path, "r") as file:
        data = file.read().strip()
        items = data.split(", ")
        return [{"item": item} for item in items]

def parse_csv(file_path):
    with open(file_path, "r") as file:
        csv_reader = csv.DictReader(file)
        return [row for row in csv_reader]

def parse_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    data = []
    for item in root.findall("grocery_item"):
        data.append({
            "name": item.find("name").text,
            "price": float(item.find("price").text)
        })
    return data

def get_file_path(filename):
    base_dir = os.path.join(os.path.dirname(__file__), "files")
    return os.path.join(base_dir, filename)

if __name__ == "__main__":
    files = [
        "groceries.txt",
        "groceries.csv",
        "groceries.json",
        "groceries.xml"
    ]

    for file_name in files:
        file_path = get_file_path(file_name)
        try:
            data = parse_file(file_path)
            print(f"\nParsed data from {file_name}:")
            print(data)
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
