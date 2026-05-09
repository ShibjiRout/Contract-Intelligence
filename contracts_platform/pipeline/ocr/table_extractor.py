def extract_tables(page_result) -> list[dict]:
    """
    Given an Azure AnalyzeResult page object, extract tables as list of dicts:
    {"headers": list[str], "rows": list[list[str]]}

    Each table's cells are iterated to reconstruct row/column structure.
    The first row is treated as headers; remaining rows are data rows.
    """
    tables = []
    for table in getattr(page_result, "tables", []):
        cells = getattr(table, "cells", [])
        if not cells:
            continue

        max_row = max(c.row_index for c in cells) + 1
        max_col = max(c.column_index for c in cells) + 1

        grid: list[list[str]] = [[""] * max_col for _ in range(max_row)]
        for cell in cells:
            grid[cell.row_index][cell.column_index] = cell.content or ""

        headers: list[str] = grid[0] if max_row > 0 else []
        rows: list[list[str]] = grid[1:] if max_row > 1 else []
        tables.append({"headers": headers, "rows": rows})

    return tables
