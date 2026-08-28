from pathlib import Path
from datetime import datetime

def metadata_extractor(file_path):
    file = Path(file_path)
    info = file.stat()
    metadata = {
        "name" : file.name,
        "extension" : file.suffix,
        "path" : str(file.resolve()),
        "size" : info.st_size,
        "created" : str(datetime.fromtimestamp(info.st_ctime)),
        "last modified" : str(datetime.fromtimestamp(info.st_mtime)),
        "last accessed" : str(datetime.fromtimestamp(info.st_atime))
    }
    return metadata

print(metadata_extractor("D:/Downloads/Project_Outline_Detailed.pdf"))