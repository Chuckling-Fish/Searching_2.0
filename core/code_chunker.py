from dataclasses import dataclass


@dataclass
class CodeChunk:
    language: str
    chunk_type: str
    name: str
    start_line: int
    end_line: int
    code: str
    parent_name: str = ""
    behavior: str = ""


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

    # Python, Java, and some C++ nodes have a direct "name" field.
    name_node = node.child_by_field_name("name")

    if name_node is not None:
        return source[
            name_node.start_byte:name_node.end_byte
        ].decode("utf-8")

    # C++ function_definition stores the function name inside the declarator.
    declarator = node.child_by_field_name("declarator")

    if declarator is not None:

        current = declarator

        # Walk through nested declarators.
        while current is not None:

            nested = current.child_by_field_name(
                "declarator"
            )

            if nested is None:
                break

            current = nested

        # At this point, C++ may give us: identifier / field_identifier
        if current.type in {
            "identifier",
            "field_identifier"
        }:
            return source[
                current.start_byte:current.end_byte
            ].decode("utf-8")

        # Some declarators may still contain the name as a field.
        final_name = current.child_by_field_name("name")
        if final_name is not None:
            return source[
                final_name.start_byte:final_name.end_byte
            ].decode("utf-8")
    return ""


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

    def visit(node, parent_name=""):

        # Is this node something we want to turn into a chunk?
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
                parent_name=parent_name,
            )

            chunks.append(chunk)
            # Build the full parent context
            if name:
                if parent_name:
                    parent_name = f"{parent_name}.{name}"
                else:
                    parent_name = name

        # Continue through the AST
        for child in node.children:
            visit(child, parent_name)

    visit(tree.root_node)

    return chunks