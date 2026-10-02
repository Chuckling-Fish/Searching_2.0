from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_cpp as tscpp

from core.code_chunker import extract_chunks


def test_python_class_and_method_parent():

    source = """class Calculator:
    def add(self, a, b):
        return a + b
"""

    PYTHON_LANGUAGE = Language(tspython.language())
    parser = Parser(PYTHON_LANGUAGE)

    tree = parser.parse(
        source.encode("utf-8")
    )

    chunks = extract_chunks(
        language_id="python",
        language_name="Python",
        tree=tree,
        source=source.encode("utf-8")
    )

    assert len(chunks) == 2

    class_chunk = chunks[0]
    method_chunk = chunks[1]

    assert class_chunk.chunk_type == "class"
    assert class_chunk.name == "Calculator"
    assert class_chunk.parent_name == ""

    assert method_chunk.chunk_type == "function"
    assert method_chunk.name == "add"
    assert method_chunk.parent_name == "Calculator"


def test_python_nested_function_parent():

    source = """class Calculator:
    def add(self, a, b):
        def helper(x):
            return x * 2
        return helper(a + b)
"""

    PYTHON_LANGUAGE = Language(tspython.language())
    parser = Parser(PYTHON_LANGUAGE)

    tree = parser.parse(
        source.encode("utf-8")
    )

    chunks = extract_chunks(
        language_id="python",
        language_name="Python",
        tree=tree,
        source=source.encode("utf-8")
    )

    assert len(chunks) == 3

    class_chunk = chunks[0]
    method_chunk = chunks[1]
    helper_chunk = chunks[2]

    assert class_chunk.name == "Calculator"
    assert class_chunk.parent_name == ""

    assert method_chunk.name == "add"
    assert method_chunk.parent_name == "Calculator"

    assert helper_chunk.name == "helper"
    assert helper_chunk.parent_name == "Calculator.add"


def test_cpp_class_and_function_parent():

    source = """class Calculator {
public:
    int add(int a, int b) {
        return a + b;
    }
};
"""

    CPP_LANGUAGE = Language(tscpp.language())
    parser = Parser(CPP_LANGUAGE)

    tree = parser.parse(
        source.encode("utf-8")
    )

    chunks = extract_chunks(
        language_id="cpp",
        language_name="C++",
        tree=tree,
        source=source.encode("utf-8")
    )

    assert len(chunks) == 2

    class_chunk = chunks[0]
    function_chunk = chunks[1]

    assert class_chunk.chunk_type == "class"
    assert class_chunk.name == "Calculator"
    assert class_chunk.parent_name == ""

    assert function_chunk.chunk_type == "function"
    assert function_chunk.name == "add"
    assert function_chunk.parent_name == "Calculator"


def test_java_class_and_method_parent():

    source = """class Calculator {
    int add(int a, int b) {
        return a + b;
    }
}
"""

    from tree_sitter import Language, Parser
    import tree_sitter_java as tsjava

    JAVA_LANGUAGE = Language(tsjava.language())
    parser = Parser(JAVA_LANGUAGE)

    tree = parser.parse(
        source.encode("utf-8")
    )

    chunks = extract_chunks(
        language_id="java",
        language_name="Java",
        tree=tree,
        source=source.encode("utf-8")
    )

    assert len(chunks) == 2

    class_chunk = chunks[0]
    method_chunk = chunks[1]

    assert class_chunk.chunk_type == "class"
    assert class_chunk.name == "Calculator"
    assert class_chunk.parent_name == ""

    assert method_chunk.chunk_type == "method"
    assert method_chunk.name == "add"
    assert method_chunk.parent_name == "Calculator"
