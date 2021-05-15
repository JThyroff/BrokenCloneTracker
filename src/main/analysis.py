from src.main.data import FileChange


def is_file_affected_at_commit(file: str, affected_files: [FileChange]) -> bool:
    return file in [e.uniform_path for e in affected_files]
