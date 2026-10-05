from pathlib import Path

from core.parser_manager import ParserManager
from core.code_chunker import extract_chunks
from analysis.behavior_analyzer import analyze_cpp_function
from core.language_registry import create_default_registry
from database.code_database import CodeDatabase


class CodeIndexer:

    def __init__(self):

        self.parser_manager = ParserManager()
        self.registry = create_default_registry()
        self.database = CodeDatabase()

    def index_file(self, file_path):

        file_path = Path(file_path).expanduser().resolve()

        # Detect language from file extension
        language_config = self.registry.detect(
            str(file_path)
        )

        if language_config is None:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}"
            )

        # Find language ID
        language_id = None

        for lang_id, config in self.registry.languages.items():

            if config == language_config:
                language_id = lang_id
                break

        # Read source code
        source = file_path.read_text(
            encoding="utf-8"
        )

        # Parse source code
        tree = self.parser_manager.parse(
            source,
            language_id
        )

        # Extract code chunks
        chunks = extract_chunks(
            language_id=language_id,
            language_name=language_config.name,
            tree=tree,
            source=source.encode("utf-8")
        )

        # Analyze C++ function behavior
        if language_id == "cpp":

            for chunk in chunks:

                if chunk.chunk_type != "function":
                    continue

                def find_function(node):

                    if (
                        node.type == "function_definition"
                        and node.start_point.row + 1 == chunk.start_line
                        and node.end_point.row + 1 == chunk.end_line
                    ):
                        return node

                    for child in node.children:

                        result = find_function(child)

                        if result is not None:
                            return result

                    return None

                function_node = find_function(
                    tree.root_node
                )

                if function_node is not None:

                    chunk.behavior = analyze_cpp_function(
                        function_node,
                        source.encode("utf-8")
                    )

        # Remove old chunks from this file
        self.database.delete_file_chunks(
            file_path
        )

        # Store new chunks
        for chunk in chunks:

            self.database.insert_chunk(
                chunk,
                file_path
            )

        return chunks

    def index_folder(self, folder_path):

        folder_path = Path(folder_path)

        all_chunks = []

        for file_path in folder_path.rglob("*"):

            if not file_path.is_file():
                continue

            try:

                chunks = self.index_file(
                    file_path
                )

                all_chunks.extend(chunks)

                print(
                    f"Indexed: {file_path}"
                )

            except ValueError:

                # Skip unsupported file types
                continue

        return all_chunks