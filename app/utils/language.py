import os


def autodetect_language(source_code: dict[str, str]) -> str:
    extensions = {
        ".py": "python",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "cpp",
        ".hpp": "cpp",
        ".h": "cpp",
        ".java": "java",
    }

    counts = {"python": 0, "cpp": 0, "java": 0}

    for filename in source_code.keys():
        ext = os.path.splitext(filename)[1].lower()
        if ext in extensions:
            counts[extensions[ext]] += 1

    detected = max(counts.items(), key=lambda x: x[1])[0]

    if counts[detected] == 0:
        return "python"

    return detected
