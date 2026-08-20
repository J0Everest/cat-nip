import re


def next_quarter(db_name: str) -> str:
    m = re.match(r"^(.*?)(\d{2})(\d{2})$", str(db_name).strip())
    if not m:
        return db_name
    prefix, yy_raw, mm_raw = m.groups()
    yy, mm = int(yy_raw), int(mm_raw)
    mm += 3
    if mm > 12:
        mm -= 12
        yy = (yy + 1) % 100
    return f"{prefix}{yy:02d}{mm:02d}"
