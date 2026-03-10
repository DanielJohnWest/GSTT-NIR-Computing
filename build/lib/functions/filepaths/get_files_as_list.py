import os
from pathlib import Path

def get_files_as_list(path, file_type):
    outputs = []
    files = os.listdir(path)
    for file in files:
        if file.lower().endswith(file_type.lower()) and '.ds_store' not in file.lower():
            outputs.append(Path(path) / file)
    return outputs

