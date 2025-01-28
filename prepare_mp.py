import argparse
import copy
import multiprocessing as mp
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from itertools import product
from os.path import join as opj
from pprint import pprint
from time import perf_counter

import chess
import chess.pgn
import wget
import zstandard
from rich import print as rprint
from rich.progress import Progress

# Global variables
EVERY_N_MONTHS = 6
NUM_GAMES_PER_MONTH = 1000
RATING_BIN_MEANS = [1000, 1200, 1600, 1800, 2000, 2200, 2400, 2600, 2800]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)}


NUM_PROCESSES = None
NUM_THREADS = None

# Progress bar in multiprocessed and multithreaded environment is a bit tricky
# This is a simple but kind a hardcoded implementation that works for the current use case
def progress_bar(progress: int, total: int, task_name: str, line: int):
    bar_length = 50  # Length of the progress bar
    filled_length = round(bar_length * progress / total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = (progress / total) * 100
    sys.stdout.write("\033[{};{}H".format(line, 1)) # should never 0,0
    sys.stdout.write(f'{task_name}|{bar}| {percent:.0f}% Complete')
    sys.stdout.flush()


def decompress_db(file_path: str) -> str:
    """
    Decompress the file if it is not already decompressed.
    """
    sys.stdout.write("\033[{};{}H".format(3+NUM_THREADS, 1))
    print("Decompressing...", flush=True)

    # check if the file is already decompressed
    if os.path.exists(file_path[:-4]):
        return file_path[:-4]

    with open(file_path, "rb") as compressed:
        dctx = zstandard.ZstdDecompressor()
        with open(file_path[:-4], "wb") as decompressed:
            dctx.copy_stream(compressed, decompressed)
    
    return file_path[:-4]


def download_db(date: str, output_dir: str, idx: int = None):
    """
    Download the database for a given date and return the path to the file.
    If the file already exists, it will return the path to the file (*.zst).
    Example date: "2013-01"
    """
    
    os.makedirs(output_dir, exist_ok=True)
    fname = f"lichess_db_standard_rated_{date}.pgn.zst"
    url = f"https://database.lichess.org/standard/{fname}"

    # check if the file is already downloaded or decompressed
    if os.path.exists(opj(output_dir, fname)) or os.path.exists(opj(output_dir, fname[:-4])):
        return opj(output_dir, fname)

    line_row = idx % NUM_THREADS + 3

    bar_name = f"Downloading {fname.split('_')[-1].split('.')[0]}"
    wget.download(url, out=output_dir, bar=lambda curr, total, width: progress_bar(curr, total, bar_name, line_row))

    return opj(output_dir, fname)

def get_rating_bin(rating: int) -> str:
    for i, bin in enumerate(RATING_BINS):
        if bin[0] <= rating <= bin[1]:
            return RATING_BIN_MEANS[i]
    return None

def get_time_control(time_control: str) -> str:
    # time_control: "X+Y"
    if time_control == "-":
        return None
    x = int(time_control.split("+")[0])
    for tempo, (min, max) in TIME_CONTROL.items():
        if min <= x <= max:
            return tempo
    return None


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
        and (game_headers.get("WhiteRatingDiff") is not None)
        and (game_headers.get("BlackRatingDiff") is not None)
        and (int(game_headers.get("WhiteRatingDiff").replace("+", "").replace("-", "")) < 15) 
        and (int(game_headers.get("BlackRatingDiff").replace("+", "").replace("-", "")) < 15) 
        and (abs(int(game_headers.get("WhiteElo")) - int(game_headers.get("BlackElo"))) < 50) 
    )


def divide_pgn_file(file_path, num_processes):
    """
    Divide the file into approximately equal parts for each process. It respects the game boundaries.
    """
    file_size = os.path.getsize(file_path)
    chunk_size = file_size // num_processes
    boundaries = [i * chunk_size for i in range(num_processes)]
    boundaries.append(file_size)  # Ensure the last chunk covers the end

    # get the actual boundaries
    with open(file_path) as pgn_db:
        for idx, start in enumerate(boundaries[:-1]):
            pgn_db.seek(start)
            
            # skip until the next game
            line = pgn_db.readline()
            while "[Event" not in line:
                line = pgn_db.readline()

            boundaries[idx] = pgn_db.tell() - len(line)

    boundaries = [[boundaries[i-1], boundaries[i]] for i in range(1, len(boundaries))]

    return boundaries


def filter_games(pgn_db_path: str, idx: int, start: int, end: int, counter: dict, lock):
    filtered_game_offsets = []
    # print(f"Processing {idx} from {start/1024**3:.2f} GB to {end/1024**3:.2f} GB", flush=True)
    
    pgn_name = pgn_db_path[:-4].split("_")[-1]

    with open(pgn_db_path) as pgn_db:
        pgn_db.seek(start)
        
        curr = pgn_db.tell()
        while curr < end:
            progress_bar(curr - start, end - start, f"Filtering pgn_name p{idx}", 3 + NUM_THREADS + idx)

            game_headers = chess.pgn.read_headers(pgn_db)
            if game_headers is None:
                print("WTF")
                break
            
            if is_game_valid(game_headers):
                mean_rating = (int(game_headers.get("WhiteElo")) + int(game_headers.get("BlackElo"))) / 2
                bin = get_rating_bin(mean_rating)
                tempo = get_time_control(game_headers.get("TimeControl"))
                
                if tempo is not None and bin is not None:
                    with lock:
                        if counter[tempo][bin] < NUM_GAMES_PER_MONTH:
                            counter[tempo][bin] += 1
                            filtered_game_offsets.append(pgn_db.tell())

            curr = pgn_db.tell()

    # save to file
    fname = pgn_db_path[:-4] + f"_filtered_p{idx}.pgn"
    with open(pgn_db_path) as pgn_db:
        with open(fname, "w") as f:
            exporter = chess.pgn.FileExporter(f)
            for offset in filtered_game_offsets:
                pgn_db.seek(offset)
                game = chess.pgn.read_game(pgn_db)
                game.accept(exporter)

    return True



def parallel_filter_games(pgn_db_path: str, num_processes: int):
    # pgn_db_path: path to the zst file
    
    pgn_db_path_decompressed = decompress_db(pgn_db_path)
    if os.path.exists(pgn_db_path):
        os.remove(pgn_db_path)
    pgn_db_path = pgn_db_path_decompressed

    boundaries = divide_pgn_file(pgn_db_path, num_processes)
    counter = {tempo: {mean: 0 for mean in RATING_BIN_MEANS} for tempo in TIME_CONTROL.keys()}

        
    with mp.Manager() as manager:
        counter = manager.dict(counter)
        lock = manager.Lock()

        with mp.Pool(num_processes) as pool:
            args = [(pgn_db_path, idx, start, end, counter, lock) for idx, (start, end) in enumerate(boundaries)]
            results = pool.starmap(filter_games, args, chunksize=1)

    sys.stdout.write("\033[{};{}H".format(3+NUM_THREADS + NUM_PROCESSES, 1))
    print("Combining filtered files...", flush=True)

    os.system(f"cat {pgn_db_path[:-4]}*_filtered_p*.pgn > {pgn_db_path[:-4]}_filtered.pgn")
    os.system(f"rm {pgn_db_path[:-4]}*_filtered_p*.pgn")
    os.system(f"rm {pgn_db_path}")


def processor_process(filter_queue, num_processes):
    """Process that handles filtering downloaded files"""

    while True:
        pgn_path = filter_queue.get()
        if pgn_path is None:  # Signal to stop
            print("Stopping processor")
            break


        start = time.perf_counter()
        parallel_filter_games(pgn_path, num_processes)
        end = time.perf_counter()

        pgn_name = pgn_path[:-8].split("_")[-1]
        sys.stdout.write("\033[{};{}H".format(3+NUM_THREADS + NUM_PROCESSES, 1))
        print(f"Filtered {pgn_name}", flush=True)


def main(args):
    global NUM_PROCESSES, NUM_THREADS
    NUM_PROCESSES = args.num_processes
    NUM_THREADS = args.num_threads

    sys.stdout.write("\033[2J\033[H") # clear screen, move cursor to top left
    print("Concurently downloading and filtering games...", flush=True)
    dates = []

    skip_dates = []
    for year, month in product(range(2015, 2025), range(1, 13, EVERY_N_MONTHS)):
        date = f"{year}-{month:02d}"
        if os.path.exists(opj(args.output_dir, f"lichess_db_standard_rated_{date}_filtered.pgn")):
            skip_dates.append(date)
        else:
            dates.append(date)

    if skip_dates:
        print("Skipping:", ", ".join(skip_dates))

    filter_queue = mp.Queue()
    processor = mp.Process(target=processor_process, args=(filter_queue, args.num_processes), name="Processor")    
    processor.start()
    
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        futures = []
        for idx, date in enumerate(dates):
            futures.append(executor.submit(download_db, date, args.output_dir, idx))

        for future in as_completed(futures):
            pgn_path = future.result()
            filter_queue.put(pgn_path)
       
    # Signal that we're done downloading
    filter_queue.put(None)

    # Wait for both processes to finish
    processor.join()



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db", help="Output directory")
    arg_parser.add_argument("-p", "--num_processes", type=int, default=8, help="Number of processes to use for filtering (default 8)")
    arg_parser.add_argument("-t", "--num_threads", type=int, default=3, help="Number of threads to use for downloading (default 3)")
    args = arg_parser.parse_args()
    
    main(args)
