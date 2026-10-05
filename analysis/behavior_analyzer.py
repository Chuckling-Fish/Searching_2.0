from tree_sitter import Node


def analyze_cpp_function(node, source):
    """
    Analyze a C++ function and generate a concise,
    human-readable description of its behavior.
    """

    behavior = []

    name_node = node.child_by_field_name("declarator")

    function_name = ""

    if name_node is not None:
        function_name = _get_function_name(
            name_node,
            source
        )

    if function_name:
        behavior.append(
            f"Function {function_name}."
        )

    declarator = node.child_by_field_name("declarator")

    parameters = (
        _find_parameters(declarator, source)
        if declarator is not None
        else []
    )

    if parameters:
        behavior.append(
            "Parameters: "
            + ", ".join(parameters)
            + "."
        )

    detected = set()

    _analyze_node(
        node,
        source,
        behavior,
        detected
    )

    return " ".join(behavior)


def _get_function_name(node, source):

    current = node

    while current is not None:

        if current.type in {
            "identifier",
            "field_identifier"
        }:
            return _text(
                current,
                source
            )

        child = current.child_by_field_name(
            "declarator"
        )

        if child is None:
            break

        current = child

    return ""


def _find_parameters(node, source):

    parameters = []

    if node is None:
        return parameters

    parameter_list = node.child_by_field_name(
        "parameters"
    )

    if parameter_list is None:
        return parameters

    for child in parameter_list.children:

        if child.type in {
            "parameter_declaration",
            "optional_parameter_declaration"
        }:

            declarator = child.child_by_field_name(
                "declarator"
            )

            if declarator is not None:

                name = _get_identifier(
                    declarator,
                    source
                )

                if name:
                    parameters.append(name)

    return parameters


def _get_identifier(node, source):

    if node.type in {
        "identifier",
        "field_identifier"
    }:
        return _text(
            node,
            source
        )

    for child in node.children:

        result = _get_identifier(
            child,
            source
        )

        if result:
            return result

    return ""


def _add_behavior(behavior, detected, message):

    if message not in detected:

        behavior.append(message)
        detected.add(message)


def _analyze_node(
    node,
    source,
    behavior,
    detected
):

    node_type = node.type

    if node_type == "return_statement":

        _add_behavior(
            behavior,
            detected,
            "Returns a result."
        )

    if node_type == "binary_expression":

        operator = node.child_by_field_name(
            "operator"
        )

        if operator is not None:

            op = _text(
                operator,
                source
            )

            if op == "*":

                _add_behavior(
                    behavior,
                    detected,
                    "Performs multiplication."
                )

            elif op == "+":

                _add_behavior(
                    behavior,
                    detected,
                    "Performs addition."
                )

            elif op == "-":

                _add_behavior(
                    behavior,
                    detected,
                    "Performs subtraction."
                )

            elif op == "/":

                _add_behavior(
                    behavior,
                    detected,
                    "Performs division."
                )

            elif op == "%":

                _add_behavior(
                    behavior,
                    detected,
                    "Performs modulo operation."
                )

            elif op in {
                "==",
                "!=",
                "<",
                ">",
                "<=",
                ">="
            }:

                _add_behavior(
                    behavior,
                    detected,
                    "Performs a comparison."
                )

        expression_text = _text(
            node,
            source
        )

        if (
            "cout" in expression_text
            and "<<" in expression_text
        ):

            _add_behavior(
                behavior,
                detected,
                "Produces console output."
            )

    if node_type in {
        "for_statement",
        "while_statement",
        "do_statement"
    }:

        _add_behavior(
            behavior,
            detected,
            "Uses a loop."
        )

    if node_type in {
        "if_statement",
        "switch_statement"
    }:

        _add_behavior(
            behavior,
            detected,
            "Uses conditional logic."
        )

    for child in node.children:

        _analyze_node(
            child,
            source,
            behavior,
            detected
        )


def _text(node, source):

    return source[
        node.start_byte:node.end_byte
    ].decode("utf-8")
