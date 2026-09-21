from core.language_registry import create_default_registry


def test_python():

    registry = create_default_registry()

    language = registry.detect("main.py")

    assert language is not None
    assert language.name == "Python"


def test_cpp():

    registry = create_default_registry()

    language = registry.detect("calculator.cpp")

    assert language is not None
    assert language.name == "C++"


def test_java():

    registry = create_default_registry()

    language = registry.detect("Main.java")

    assert language is not None
    assert language.name == "Java"


def test_unknown_language():

    registry = create_default_registry()

    language = registry.detect("notes.xyz")

    assert language is None