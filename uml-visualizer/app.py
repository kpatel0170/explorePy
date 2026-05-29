import os
import plantuml
import requests


BASE_DIR = os.getcwd()  # Get the current working directory
FILES_DIR = os.path.join(BASE_DIR, "files")  # Folder where JSON files are stored


def load_data():
    response = requests.get("https://randomuser.me/api/?format=json", timeout=5000)
    if response.status_code == 200:
        return response.json()["results"][0]
    else:
        print("Data did not load correctly")
        return None


def write_plantuml_file(res):
    nodeName = res["name"]["first"] + "_" + res["name"]["last"]
    output_path = os.path.join(FILES_DIR, "live-randomuser.txt")
    with open(output_path, "w", encoding="utf-8") as pf:
        pf.write("@startuml \n")
        pf.write("object " + nodeName + " \n")
        pf.write(nodeName + " : email = " + res["email"] + "\n")
        pf.write(nodeName + " : phone = " + res["phone"] + "\n")
        pf.write(nodeName + " : age = " + str(res["dob"]["age"]) + "\n")
        pf.write("@enduml \n")


def create_plantuml_image():
    output_path = os.path.join(FILES_DIR, "live-randomuser.txt")
    plantuml.PlantUML("http://www.plantuml.com/plantuml/img/").processes_file(
        output_path, outfile=None, errorfile=None
    )


if __name__ == "__main__":
    response_json = load_data()
    if response_json is not None:
        write_plantuml_file(response_json)
        create_plantuml_image()
