from tree_sitter import Language, Parser

import tree_sitter_python as ts_python
import tree_sitter_cpp as ts_cpp
import tree_sitter_java as ts_java

from core.language_registry import create_default_registry


class ParserManager:

    def __init__(self):

        self.registry = create_default_registry()

        self.parsers = {
            "python": Parser(
                Language(ts_python.language())
            ),

            "cpp": Parser(
                Language(ts_cpp.language())
            ),

            "java": Parser(
                Language(ts_java.language())
            ),
        }

    def parse(self, source_code, language_id):

        parser = self.parsers.get(language_id)

        if parser is None:
            raise ValueError(
                f"Unsupported language: {language_id}"
            )

        tree = parser.parse(
            source_code.encode("utf-8")
        )

        return tree