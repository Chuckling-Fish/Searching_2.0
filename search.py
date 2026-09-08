from pathlib import Path
from pypdf import PdfReader
SUPPORTED_EXTENSIONS={
    ".txt",
    ".py",
    ".cpp",
    ".md",
    ".pdf",
    ".java",
    }

folder = Path("TestFiles")

query = input("What are you searching for?")

print("\nSearch Result:\n")

for item in folder.rglob("*"):
    #for pdf files
    if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
        try:
            #for pdf files
            if item.suffix.lower() == ".pdf":
                reader = PdfReader(item)
                content = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text

            else:
                content =item.read_text()

           
            if query.lower() in content.lower():
                print("Found in:",item.name)
                print("Path:",item)
                print()
        except Exception as e:

            print(f"Could not read{item.name}: {e}")