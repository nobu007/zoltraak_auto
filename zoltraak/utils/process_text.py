def normal(text, language=None):
    lines = text.split("\n")
    inside_code_block = False
    result = []

    for _i, line in enumerate(lines):
        if line.startswith("```"):
            if not inside_code_block:
                inside_code_block = True
                if language is not None and language.lower() not in line.lower():
                    inside_code_block = False
            else:
                inside_code_block = False
        elif inside_code_block:
            result.append(line)
        else:
            result.append("# " + line)

    return "\n".join(result)
