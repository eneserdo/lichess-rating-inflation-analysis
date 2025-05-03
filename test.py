import mmap
import os
import re
import sys
import time

import chess
import chess.pgn


def filter_by_pgn(file_path, filter_func):
    count = 0
    total = 0
    with open(file_path, "r") as file:
        while True:
            pgn_header = chess.pgn.read_headers(file)
            if not pgn_header:
                break
            if filter_func(pgn_header):
                count += 1
            total += 1

    return count, total


def filter_naive(file_path, filter_func, binary=False, buffer_size=-1):
    count = 0
    total = 0
    file_size = os.path.getsize(file_path)

    with open(file_path, "r" if not binary else "rb", buffering=buffer_size) as file:
        game_lines = [file.readline()]

        while file.tell() < file_size: 
            line = file.readline()
            if not line.startswith("[Event"):
                game_lines.append(line)
            else:
                # new game starts
                if filter_func(game_lines):
                    count += 1
                game_lines = [line]
                total += 1

    return count, total


def divide_pgn_file(file_path, num_partitions):
    """
    Divide the file into approximately equal parts. It complies with the requirements of mmap (offset must be multiple of ALLOCATIONGRANULARITY, length can be anything).
    # TODO: Is it possible to have a game > ALLOCATIONGRANULARITY ?
    """
    file_size = os.path.getsize(file_path)
    page_size = mmap.ALLOCATIONGRANULARITY

    assert file_size >= page_size, f"File is smaller than the page size: {file_size:_} < {page_size:_}"


    chunk_size = file_size // num_partitions
    boundaries = [i * chunk_size for i in range(num_partitions)]
    boundaries.append(file_size)  # Ensure the last chunk covers the end

    # align starts to the page size
    boundary_pairs = []
    for i in range(1, len(boundaries)):
        start = boundaries[i-1]
        aligned_start = (start + page_size - 1) // page_size * page_size
        end = boundaries[i]
        boundary_pairs.append([aligned_start, end])

    del boundaries

    # shift the ends to cover all the games
    with open(file_path) as pgn_db:
        for idx, (start, end) in enumerate(boundary_pairs[:-1]):
            # Align start to page boundary

            pgn_db.seek(end)
            line = pgn_db.readline()
            while not line.startswith("[Event"):
                line = pgn_db.readline()
            boundary_pairs[idx][1] = pgn_db.tell() - len(line)

    # Basically, ends respect the game boundaries, but starts are aligned to the page size
    # When using mmap, at the beginning of the file, consume the first partial game
    return boundary_pairs

def consume_first_game(mmap_file):
    line = mmap_file.readline()
    while not line.startswith(b"[Event"):
        # print("c", end="", flush=True)
        line = mmap_file.readline()
    # print()
    mmap_file.seek(mmap_file.tell() - len(line))

    

def filter_mmap(file_path, filter_func, num_steps=1):
    count = 0
    total = 0
    file_size = os.path.getsize(file_path)
    
    if num_steps == 1:
        boundaries = [[0, file_size]]
    else:
        boundaries = divide_pgn_file(file_path, num_steps)

    with open(file_path, "r") as file:  # Open in binary mode with write access
        for start, end in boundaries:
            # print(f"Processing chunk {start} - {end}")
            
            with mmap.mmap(file.fileno(), length=end - start, access=mmap.ACCESS_READ, offset=start) as mmap_file:
                # consume the first partial game
                consume_first_game(mmap_file)

                # read the rest of the games
                game_lines = [mmap_file.readline()]
                
                while mmap_file.tell() < end-start:
                    line = mmap_file.readline()
                        
                    if not line.startswith(b"[Event"):
                        game_lines.append(line)
                    else:
                        # new game starts
                        if filter_func(game_lines):
                            count += 1
                        game_lines = [line]
                        total += 1
                    
                # Process the last game in the chunk
                if game_lines and filter_func(game_lines):
                    count += 1
                    total += 1

    return count, total


def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return end - start, result



# def filter_string(content_lines):
#     white_elo = None
#     black_elo = None
#     for line in content_lines:
#         if line.startswith("[WhiteElo "):
#             if "?" in line:
#                 return False
#             # regex to extract the elo
#             white_elo = int(line.split(" ")[1].strip().strip("]").strip("\""))
#         elif line.startswith("[BlackElo "):
#             if "?" in line:
#                 return False
#             black_elo = int(line.split(" ")[1].strip().strip("]").strip("\""))
        
#         if white_elo is not None and black_elo is not None:
#             break

#     if white_elo is None or black_elo is None:
#         raise ValueError("No white or black elo found")
    
#     return abs(white_elo - black_elo) < 50

# def filter_byte(content_lines):
#     white_elo = None
#     black_elo = None
#     for line in content_lines:
#         if line.startswith(b"[WhiteElo "):
#             if b"?" in line:
#                 return False
#             # regex to extract the elo
#             white_elo = int(line.split(b" ")[1].strip().strip(b"]").strip(b"\""))
#         elif line.startswith(b"[BlackElo "):
#             if b"?" in line:
#                 return False
#             black_elo = int(line.split(b" ")[1].strip().strip(b"]").strip(b"\""))
        
#         if white_elo is not None and black_elo is not None:
#             break

#     if white_elo is None or black_elo is None:
#         raise ValueError("No white or black elo found")
    
#     return abs(white_elo - black_elo) < 50


def is_game_valid(game_headers: dict) -> bool:
    """
    Discard:
    - casual games
    - players with high rating deviation
    - anonymous players
    - games with high rating difference
    """
    return (
        ("rated" in game_headers.get("Event").lower())
        and ("?" not in game_headers.get("White")) 
        and ("?" not in game_headers.get("Black"))
        and ("WhiteRatingDiff" in game_headers)
        and ("BlackRatingDiff" in game_headers)
        and (int(game_headers.get("WhiteRatingDiff").replace("+", "").replace("-", "")) < 15) 
        and (int(game_headers.get("BlackRatingDiff").replace("+", "").replace("-", "")) < 15) 
        and (abs(int(game_headers.get("WhiteElo")) - int(game_headers.get("BlackElo"))) < 50) 
        and ("TimeControl" in game_headers)
    )

def filter_byte(content_lines):
    header = {}
    for line in content_lines:
        if not line.startswith(b"["):
            continue
        key, value = line.split(b" ", 1)
        key = key.strip(b"[").decode()
        value = value.strip().strip(b"]").strip(b"\"").decode()
        header[key] = value
    
    return is_game_valid(header)
    
    

def temp():
    # create a dummy txt file with 1000 lines
    with open("dummy.txt", "w") as f:
        for i in range(1000):
            f.write(f"line {i}\n")

    # read with mmap
    with open("dummy.txt", "r+b") as f:
        mmap_file = mmap.mmap(f.fileno(), length=100, access=mmap.ACCESS_READ, offset=4*1024)
        print(mmap_file.read())


if __name__ == "__main__":
    fname = "dummy_db/dummy.pgn"
    fsize = os.path.getsize(fname)
    print(f"file size: {fsize:_}\n")

    elapsed, result = measure_time(filter_by_pgn, fname, is_game_valid)
    print(f"filter_by_pgn: {round(elapsed, 5)}s, {result}")

    # elapsed, result = measure_time(filter_naive, fname, filter_string, binary=False)
    # print(f"filter_naive: {round(elapsed, 5)}s, {result}")

    elapsed, result = measure_time(filter_mmap, fname, filter_byte)
    print(f"filter_mmap: {round(elapsed, 5)}s, {result}")

    elapsed, result = measure_time(filter_mmap, fname, filter_byte, num_steps=5)
    print(f"filter_mmap 1/5: {round(elapsed, 5)}s, {result}")

    elapsed, result = measure_time(filter_mmap, fname, filter_byte, num_steps=10)
    print(f"filter_mmap 1/10: {round(elapsed, 5)}s, {result}")
