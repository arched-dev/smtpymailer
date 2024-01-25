from pathlib import Path


def find_project_root(current_path, marker=".git"):
    """
    Traverse up from the current path until a directory containing the marker is found.
    """
    current_file_path = Path(__file__)
    current_path = Path(current_path).resolve()
    for parent in current_path.parents:
        if (parent / marker).exists():
            return parent
    return None  # or raise an exception if you prefer
