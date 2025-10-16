from colorama import Fore as color, Style as style
import time
import math
import re

def is_perfect_square(n: int) -> bool:
    r = int(math.isqrt(n))
    return r * r == n

def val_to_char(v: int) -> str:
    # 0 -> blank; 1-9 -> '1'..'9'; 10+ -> 'A'.. (supports up to 35 -> 'Z')
    if v == 0:
        return ' '
    if 1 <= v <= 9:
        return str(v)
    return chr(ord('A') + (v - 10))

def char_to_val(ch: str) -> int | None:
    # Map space/0/. to 0; digits to ints; letters A-Z to 10..35
    if ch in (' ', '0', '.'):
        return 0
    if ch.isdigit():
        return int(ch)
    ch = ch.upper()
    if 'A' <= ch <= 'Z':
        return 10 + (ord(ch) - ord('A'))
    return None

def allowed_symbols(size: int) -> set[str]:
    # Symbols accepted per cell in input files: 0 . (blank), 1-9, A.. as needed
    syms = {'0', '.'}
    for i in range(1, min(size, 9) + 1):
        syms.add(str(i))
    if size > 9:
        for i in range(size - 9):
            syms.add(chr(ord('A') + i))
            syms.add(chr(ord('a') + i))
    return syms

def issolved(board, size: int):
    target = list(range(1, size + 1))
    # rows
    for row in board:
        if sorted(row) != target:
            return False
    # columns
    for i in range(size):
        column = [board[j][i] for j in range(size)]
        if sorted(column) != target:
            return False
    # boxes
    box = int(math.isqrt(size))
    for bi in range(box):
        for bj in range(box):
            subgrid = [board[x][y]
                       for x in range(bi * box, (bi + 1) * box)
                       for y in range(bj * box, (bj + 1) * box)]
            if sorted(subgrid) != target:
                return False
    return True

def load_sudokus(path="sudokus.txt", *, size: int = 9):
    """Load sudokus of given size from a text file.
    Each puzzle is 'size' lines. Each line must contain at least 'size' valid symbols:
      - blanks: 0 or .
      - values: 1-9 and then A, B, C... for 10, 11, 12... (case-insensitive)
    Lines may contain extra characters; invalid chars are ignored. Puzzles are separated by blank lines or '#'-comments.
    """
    puzzles = []
    current = []
    syms = allowed_symbols(size)
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    if not line and len(current) == size:
                        puzzles.append(current)
                        current = []
                    continue
                filtered = [ch for ch in raw if ch in syms]
                if len(filtered) < size:
                    continue
                filtered = filtered[:size]
                row_vals = []
                for ch in filtered:
                    v = char_to_val(ch)
                    if v is None:
                        v = 0
                    row_vals.append(v)
                current.append(row_vals)
                if len(current) == size:
                    puzzles.append(current)
                    current = []
        if len(current) == size:
            puzzles.append(current)
    except FileNotFoundError:
        print(f"{color.RED}sudokus.txt not found{style.RESET_ALL}")
    return puzzles

def solve_board(board, size: int):
    nums = list(range(1, size + 1))
    box = int(math.isqrt(size))
    # Track givens to color only solver-added numbers at report time
    given_mask = [[cell != 0 for cell in row] for row in board]

    # Legacy per-number tracking matrices (kept for parity with existing code)
    for i in range(size):
        exec(f"board_{i}s = [[0 for _ in range(size)] for _ in range(size)]", {'size': size}, globals())
        for r_idx, row in enumerate(board):
            for c_idx, cell in enumerate(row):
                if cell == i + 1:
                    exec(f"board_{i}s[{r_idx}][{c_idx}] = 1")

    cycles_without_change = 0
    cycles = 0
    start = time.time()

    def percent_solved() -> float:
        total = size * size
        filled = sum(1 for r in range(size) for c in range(size) if board[r][c] != 0)
        return (filled / total) * 100.0

    while not issolved(board, size):
        cycles += 1
        progressed = False

        # Build all boxes flattened
        grids = [
            [board[x][y]
             for x in range(bi * box, (bi + 1) * box)
             for y in range(bj * box, (bj + 1) * box)]
            for bi in range(box) for bj in range(box)
        ]

        # Rule: if only one blank in a box, fill it
        for g_idx, grid in enumerate(grids):
            if grid.count(0) == 1:
                missing_number = list(set(nums) - set(grid))[0]
                zero_index = grid.index(0)
                # Map grid index + local zero_index to global row/col
                grid_row = (g_idx // box) * box + (zero_index // box)
                grid_col = (g_idx % box) * box + (zero_index % box)
                if board[grid_row][grid_col] == 0:
                    board[grid_row][grid_col] = missing_number
                    exec(f"board_{missing_number - 1}s[{grid_row}][{grid_col}] = 1")
                    progressed = True

        # Row singles for a specific number (generalized)
        for r_idx, row in enumerate(board):
            if row.count(0) > 1:
                for number in nums:
                    if number not in row:
                        possible_positions = []
                        for c_idx in range(size):
                            if row[c_idx] == 0:
                                # Check box and column constraints
                                grid_row = r_idx // box
                                grid_col = c_idx // box
                                grid = [board[x][y]
                                        for x in range(grid_row * box, (grid_row + 1) * box)
                                        for y in range(grid_col * box, (grid_col + 1) * box)]
                                column_vals = [board[r][c_idx] for r in range(size)]
                                if number not in grid and number not in column_vals:
                                    possible_positions.append(c_idx)
                        if len(possible_positions) == 1:
                            c_idx = possible_positions[0]
                            if board[r_idx][c_idx] == 0:
                                board[r_idx][c_idx] = number
                                exec(f"board_{number - 1}s[{r_idx}][{c_idx}] = 1")
                                progressed = True

        # Column singles for a specific number (generalized)
        for c_idx in range(size):
            column = [board[r_idx][c_idx] for r_idx in range(size)]
            if column.count(0) > 1:
                for number in nums:
                    if number not in column:
                        possible_positions = []
                        for r_idx in range(size):
                            if column[r_idx] == 0:
                                grid_row = r_idx // box
                                grid_col = c_idx // box
                                grid = [board[x][y]
                                        for x in range(grid_row * box, (grid_row + 1) * box)
                                        for y in range(grid_col * box, (grid_col + 1) * box)]
                                row_vals = board[r_idx]
                                if number not in grid and number not in row_vals:
                                    possible_positions.append(r_idx)
                        if len(possible_positions) == 1:
                            r_idx = possible_positions[0]
                            if board[r_idx][c_idx] == 0:
                                board[r_idx][c_idx] = number
                                exec(f"board_{number - 1}s[{r_idx}][{c_idx}] = 1")
                                progressed = True

        # Rows with 2–5 blanks: place numbers that have exactly one valid column
        for r_idx, row in enumerate(board):
            zero_indices = [c for c, v in enumerate(row) if v == 0]
            if 2 <= len(zero_indices) <= 5:
                missing_numbers = [n for n in nums if n not in row]
                for number in missing_numbers:
                    candidates = []
                    for c_idx in zero_indices:
                        col_vals = [board[r][c_idx] for r in range(size)]
                        if number not in col_vals:
                            candidates.append(c_idx)
                    if len(candidates) == 1:
                        c_idx = candidates[0]
                        if board[r_idx][c_idx] == 0:
                            board[r_idx][c_idx] = number
                            exec(f"board_{number - 1}s[{r_idx}][{c_idx}] = 1")
                            progressed = True

        # Columns with 2–5 blanks: place numbers that have exactly one valid row
        for c_idx in range(size):
            column = [board[r_idx][c_idx] for r_idx in range(size)]
            zero_indices = [r for r, v in enumerate(column) if v == 0]
            if 2 <= len(zero_indices) <= 5:
                missing_numbers = [n for n in nums if n not in column]
                for number in missing_numbers:
                    candidates = []
                    for r_idx in zero_indices:
                        row_vals = board[r_idx]
                        if number not in row_vals:
                            candidates.append(r_idx)
                    if len(candidates) == 1:
                        r_idx = candidates[0]
                        if board[r_idx][c_idx] == 0:
                            board[r_idx][c_idx] = number
                            exec(f"board_{number - 1}s[{r_idx}][{c_idx}] = 1")
                            progressed = True

        # Fill rows that have exactly one blank (with column/grid validation)
        for r_idx, row in enumerate(board):
            if row.count(0) == 1:
                missing_number, = set(nums) - set(row)
                c_idx = row.index(0)
                column = [board[r][c_idx] for r in range(size)]
                grid_row = r_idx // box
                grid_col = c_idx // box
                grid = [board[x][y]
                        for x in range(grid_row * box, (grid_row + 1) * box)
                        for y in range(grid_col * box, (grid_col + 1) * box)]
                if missing_number not in column and missing_number not in grid:
                    board[r_idx][c_idx] = missing_number
                    exec(f"board_{missing_number - 1}s[{r_idx}][{c_idx}] = 1")
                    progressed = True

        # Rule 7: sole candidates per cell (eliminate row/col/box values)
        for br in range(box):
            for bc in range(box):
                for r in range(br * box, (br + 1) * box):
                    for c in range(bc * box, (bc + 1) * box):
                        if board[r][c] == 0:
                            row_vals = set(board[r])
                            col_vals = {board[i][c] for i in range(size)}
                            box_vals = {
                                board[x][y]
                                for x in range(br * box, (br + 1) * box)
                                for y in range(bc * box, (bc + 1) * box)
                            }
                            row_vals.discard(0)
                            col_vals.discard(0)
                            box_vals.discard(0)
                            used = row_vals | col_vals | box_vals
                            candidates = list(set(nums) - used)
                            if len(candidates) == 1:
                                number = candidates[0]
                                board[r][c] = number
                                exec(f"board_{number - 1}s[{r}][{c}] = 1")
                                progressed = True

        if progressed:
            cycles_without_change = 0
        else:
            cycles_without_change += 1

        percent = percent_solved()
        progress_color = (
            color.RED if percent < 25 else
            color.YELLOW if percent < 50 else
            color.GREEN if percent < 75 else
            color.BLUE
        )
        print(f"{progress_color}Cycle {cycles} | Percent of board solved: {percent:.2f}%{style.RESET_ALL}")
        if cycles_without_change > 5:
            break

    # Print final board state (no commas/brackets, blanks shown as spaces). New values in green.
    print("Final board state:")
    for r, row in enumerate(board):
        rendered = []
        for c, cell in enumerate(row):
            ch = val_to_char(cell)
            if cell != 0 and not given_mask[r][c]:
                rendered.append(f"{color.GREEN}{ch}{style.RESET_ALL}")
            else:
                rendered.append(ch)
        print(' '.join(rendered))
    # Solved/Unsolved notification in color
    if issolved(board, size):
        ms = round((time.time() - start) * 1000, 2)
        print(f"{color.GREEN}Board solved in {ms} milliseconds{style.RESET_ALL}")
    else:
        print(f"{color.RED}Board unsolved{style.RESET_ALL}")

def token_to_val(tok: str, size: int) -> int | None:
    t = tok.strip()
    if t == '' or t == '.':
        return 0
    if t.isdigit():
        v = int(t)
        return v if 0 <= v <= size else None
    if len(t) == 1 and t.isalpha():
        v = char_to_val(t)
        if v is not None and v <= size:
            return v
    return None

def parse_row_input(s: str, size: int) -> list[int] | None:
    # Mode 1: exactly 'size' single-character symbols (0/./space for blank; 1-9,A..)
    syms = allowed_symbols(size) | {' '}
    chars = [ch for ch in s if ch in syms]
    if len(chars) == size:
        row: list[int] = []
        for ch in chars:
            v = char_to_val(ch)
            if v is None or v > size:
                return None
            row.append(v)
        return row
    # Mode 2: tokenized input (split on non-alphanumeric, e.g., dots/spaces/commas)
    tokens = [t for t in re.split(r'[^A-Za-z0-9]+', s) if t != '']
    if len(tokens) != size:
        return None
    row2: list[int] = []
    for t in tokens:
        v = token_to_val(t, size)
        if v is None:
            return None
        row2.append(v)
    return row2

if __name__ == "__main__":
    try:
        while True:
            # Select size
            raw_size = input("Enter board size (perfect square: 4, 9, 16, 25, ...) [9] or Q to quit > ").strip()
            if raw_size.lower().startswith('q'):
                print("Goodbye.")
                break
            size = 9
            if raw_size:
                try:
                    size = int(raw_size)
                    if size < 1 or not is_perfect_square(size):
                        print("Size must be a positive perfect square (e.g., 4, 9, 16, 25).")
                        continue
                except ValueError:
                    print("Please enter a number (e.g., 9, 16, 25) or Q to quit.")
                    continue

            choice = input("Enter an external board? (True, False) or Q to cancel > ").strip()
            if choice.lower().startswith('q'):
                continue

            if choice.lower() == "true":
                board = []
                sym_list = ''.join(sorted(allowed_symbols(size) - {'.', '0', ' '}))
                print(f"Enter {size} rows. You can:")
                print(f"- Type exactly {size} single characters [{sym_list}] (use space/'.'/0 for blanks), or")
                print(f"- Provide {size} tokens separated by spaces/commas/dots (e.g., for 16x16: 9.13.12.0.0.0.14.11.0.0.6.4.16.10.0.3)")
                print(f"For size > 9, letters map as A=10, B=11, ...")
                for i in range(size):
                    while True:
                        s = input(f"Enter row {i + 1} (length {size} or {size} tokens): ")
                        row = parse_row_input(s, size)
                        if row is None:
                            print(f"Invalid row. Use {size} single symbols or {size} tokens (0/./space for blanks; 1-9 and A.. for values).")
                            continue
                        board.append(row)
                        break
                solve_board(board, size)
            else:
                puzzles = load_sudokus("sudokus.txt", size=size)
                if not puzzles:
                    print(f"{color.RED}No sudokus found in sudokus.txt for size {size}{style.RESET_ALL}")
                    continue
                print(f"Found {len(puzzles)} sudokus in sudokus.txt (size {size}x{size})")
                while True:
                    sel = input(f"Select puzzle number (1-{len(puzzles)}) or Q to cancel: ").strip()
                    if sel.lower().startswith('q'):
                        board = None
                        break
                    try:
                        idx = int(sel)
                        if 1 <= idx <= len(puzzles):
                            board = [row[:] for row in puzzles[idx - 1]]
                            break
                    except ValueError:
                        pass
                    print("Invalid selection.")
                if board is None:
                    continue
                solve_board(board, size)
            # Loop continues to allow solving another puzzle
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")