from dataclasses import dataclass


@dataclass
class CodeChunk:
    language: str
    chunk_type: str
    name: str
    start_line: int
    end_line: int
    code: str


# Tree-sitter node type → our common chunk type
STRUCTURE_TYPES = {

    "python": {
        "function_definition": "function",
        "class_definition": "class",
    },

    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "struct",
        "namespace_definition": "namespace",
    },

    "java": {
        "method_declaration": "method",
        "class_declaration": "class",
        "interface_declaration": "interface",
        "enum_declaration": "enum",
        "constructor_declaration": "constructor",
    },
}


def get_node_name(node, source):

    name_node = node.child_by_field_name("name")

    if name_node is None:
        return ""

    return source[
        name_node.start_byte:name_node.end_byte
    ]


def extract_chunks(
    language_id,
    language_name,
    tree,
    source
):

    chunks = []

    structure_map = STRUCTURE_TYPES.get(
        language_id,
        {}
    )

    def visit(node):

        # Is this node something we want
        # to turn into a chunk?
        if node.type in structure_map:

            chunk_type = structure_map[node.type]

            name = get_node_name(
                node,
                source
            )

            code = source[
                node.start_byte:node.end_byte
            ]

            chunk = CodeChunk(
                language=language_name,
                chunk_type=chunk_type,
                name=name,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                code=code,
            )

            chunks.append(chunk)

        # Continue through the AST
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    return chunks