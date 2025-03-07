# write a code that creates csv text lines from the given list of codes and group code

def generate_csv(bottle_codes: list[str], group_code: str) -> str:
    csv_lines = []
    for code in bottle_codes:
        csv_lines.append(f"{code},{group_code}")
    return "\n".join(csv_lines)
