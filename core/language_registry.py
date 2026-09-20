from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageConfig:
    name: str
    extensions: tuple[str, ...]
    parser_module: str


class LanguageRegistry:

    def __init__(self):

        self.languages = {
            "python": LanguageConfig(
                name="Python",
                extensions=(".py", ".pyw"),
                parser_module="tree_sitter_python",
            ),

            "cpp": LanguageConfig(
                name="C++",
                extensions=(".cpp", ".cc", ".cxx", ".hpp"),
                parser_module="tree_sitter_cpp",
            ),

            "java": LanguageConfig(
                name="Java",
                extensions=(".java",),
                parser_module="tree_sitter_java",
            ),
        }

        self.extension_map = {}

        for language_id, config in self.languages.items():
            for extension in config.extensions:
                self.extension_map[extension] = language_id

    def detect(self, file_path):

        extension = "." + file_path.rsplit(".", 1)[-1].lower()

        language_id = self.extension_map.get(extension)

        if language_id is None:
            return None

        return self.languages[language_id]

    def get(self, language_id):

        return self.languages.get(language_id)


def create_default_registry():
    return LanguageRegistry()