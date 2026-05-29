from pathlib import Path


BASE_DIR = Path(__file__).parent
NAMES_PATH = BASE_DIR / "Input" / "Names" / "invited_names.txt"
LETTER_PATH = BASE_DIR / "Input" / "Letters" / "starting_letter.txt"
OUTPUT_DIR = BASE_DIR / "Output" / "ReadyToSend"


def main():
    names = NAMES_PATH.read_text().splitlines()
    starting_letter_contents = LETTER_PATH.read_text()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name in names:
        cleaned_name = name.strip()
        new_letter_contents = starting_letter_contents.replace("[name]", cleaned_name)
        (OUTPUT_DIR / f"letter_for_{cleaned_name}.txt").write_text(new_letter_contents)


if __name__ == "__main__":
    main()
