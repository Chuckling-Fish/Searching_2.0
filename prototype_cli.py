from pathlib import Path

from database.code_hybrid_search import hybrid_search
from analysis.code_output_analyzer import analyze_cpp_file


def print_result(number, result):
    print()
    print("=" * 70)
    print(f"RESULT {number}")
    print("=" * 70)

    print(f"File:      {result['file_name']}")
    print(f"Directory: {Path(result['file_path']).parent}")
    print(f"Language:  {result['language']}")
    print(f"Type:      {result['chunk_type']}")
    print(f"Name:      {result['name']}")
    print(f"Lines:     {result['start_line']}-{result['end_line']}")

    if result.get("behavior"):
        print()
        print("Behavior:")
        print(result["behavior"])

    print()
    print("Code:")
    print("-" * 70)
    print(result["code"])
    print("-" * 70)


def analyze_output(result):
    language = (result.get("language") or "").lower()

    if language not in {"c++", "cpp"}:
        print()
        print("Output analysis currently supports C++ only.")
        return

    file_path = result["file_path"]

    print()
    print("Source file:")
    print(file_path)

    print()
    print("Program input:")
    print("Enter the input exactly as the C++ program expects.")
    print("Press Enter on an empty line when finished.")

    input_lines = []

    while True:
        line = input()

        if line == "":
            break

        input_lines.append(line)

    input_data = "\n".join(input_lines) + "\n"

    print()
    print("Running complete C++ source file...")
    print("Timeout: 3 seconds")

    analysis = analyze_cpp_file(
        file_path,
        timeout=3,
        input_data=input_data
    )

    print()
    print("Output Analysis")
    print("-" * 70)

    print(f"Status: {analysis['status']}")

    if analysis.get("output"):
        print()
        print("Program Output:")
        print(analysis["output"])

    if analysis.get("error"):
        print()
        print("Error:")
        print(analysis["error"])

    if "return_code" in analysis:
        print()
        print(f"Return code: {analysis['return_code']}")

    print("-" * 70)


def choose_mode():
    print()
    print("Search mode:")
    print("1. Hybrid")
    print("2. Keyword")
    print("3. Semantic")

    choice = input("Choose [1]: ").strip()

    if choice == "2":
        return "keyword"

    if choice == "3":
        return "semantic"

    return "hybrid"


def main():

    print()
    print("=" * 70)
    print("                 CODE SEARCH PROTOTYPE")
    print("=" * 70)

    while True:

        query = input(
            "\nSearch query "
            "(or type 'exit' to quit): "
        ).strip()

        if query.lower() in {"exit", "quit"}:
            print("\nExiting code search.")
            break

        if not query:
            print("Please enter a search query.")
            continue

        mode = choose_mode()

        extension = input(
            "\nFile extension "
            "(example: .cpp, .py, .java; press Enter for all): "
        ).strip()

        if not extension:
            extension = None

        print()
        print("Searching...")

        try:

            results = hybrid_search(
                query=query,
                mode=mode,
                extension=extension,
                limit=5
            )

        except Exception as error:

            print()
            print("Search error:")
            print(error)
            continue

        print()
        print("=" * 70)
        print(f"FOUND {len(results)} RESULT(S)")
        print("=" * 70)

        if not results:
            print("No matching code found.")
            continue

        for index, result in enumerate(results, start=1):

            print()
            print(
                f"{index}. "
                f"{result['file_name']} "
                f"→ {result['name']} "
                f"({result['language']})"
            )

            print(
                f"   Directory: "
                f"{Path(result['file_path']).parent}"
            )

            print(
                f"   Lines: "
                f"{result['start_line']}-"
                f"{result['end_line']}"
            )

        while True:

            selection = input(
                "\nSelect result number "
                "(or press Enter for new search): "
            ).strip()

            if not selection:
                break

            try:

                selected = int(selection)

                if not 1 <= selected <= len(results):
                    print("Invalid result number.")
                    continue

            except ValueError:

                print("Please enter a number.")
                continue

            result = results[selected - 1]

            print_result(
                selected,
                result
            )

            while True:

                action = input(
                    "\nActions:\n"
                    "[1] Show code\n"
                    "[2] Behavior\n"
                    "[3] Analyze output\n"
                    "[4] Back\n"
                    "Choose: "
                ).strip()

                if action == "1":

                    print()
                    print(result["code"])

                elif action == "2":

                    print()
                    print("Behavior:")
                    print(
                        result.get(
                            "behavior",
                            "No behavior analysis available."
                        )
                    )

                elif action == "3":

                    analyze_output(result)

                elif action == "4":

                    break

                else:

                    print("Invalid choice.")


if __name__ == "__main__":
    main()