import subprocess
import tempfile
from pathlib import Path


def analyze_cpp_output(code, timeout=3, input_data=""):
    """
    Compile and run a standalone C++ code string.
    """

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        source_file = temp_path / "program.cpp"
        executable = temp_path / "program"

        source_file.write_text(
            code,
            encoding="utf-8"
        )

        try:

            compile_process = subprocess.run(
                [
                    "g++",
                    str(source_file),
                    "-std=c++17",
                    "-O0",
                    "-o",
                    str(executable)
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

        except subprocess.TimeoutExpired:

            return {
                "status": "compile_timeout",
                "output": "",
                "error": f"Compilation exceeded {timeout} seconds."
            }

        if compile_process.returncode != 0:

            return {
                "status": "compile_error",
                "output": "",
                "error": compile_process.stderr.strip()
            }

        try:

            run_process = subprocess.run(
                [str(executable)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )

        except subprocess.TimeoutExpired:

            return {
                "status": "timeout",
                "output": "",
                "error": f"Program exceeded {timeout} seconds."
            }

        return {
            "status": (
                "success"
                if run_process.returncode == 0
                else "runtime_error"
            ),
            "output": run_process.stdout.strip(),
            "error": run_process.stderr.strip(),
            "return_code": run_process.returncode
        }


def analyze_cpp_file(file_path, timeout=3, input_data=""):
    """
    Read and execute a complete C++ source file.
    """

    path = Path(file_path).expanduser().resolve()

    if not path.exists():

        return {
            "status": "file_not_found",
            "output": "",
            "error": f"Source file not found: {path}"
        }

    if path.suffix.lower() not in {
        ".cpp",
        ".cc",
        ".cxx"
    }:

        return {
            "status": "unsupported",
            "output": "",
            "error": (
                "Output analysis currently supports "
                "C++ source files."
            )
        }

    try:

        code = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

    except OSError as error:

        return {
            "status": "read_error",
            "output": "",
            "error": str(error)
        }

    return analyze_cpp_output(
        code,
        timeout=timeout,
        input_data=input_data
    )

