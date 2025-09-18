import json


def load_credentials(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[red]Error: File {file_path} not found![/red]")
        return None
    except json.JSONDecodeError:
        print(f"[red]Error: File {file_path} is not a valid JSON![/red]")
        return None
