import argparse
from collections import Counter
import copy
from functools import partial
from itertools import product
import os
from os.path import join as opj
from pprint import pprint
import sys
from time import perf_counter
import time
import wget
import zstandard
import chess
import chess.pgn
from rich import print as rprint
import multiprocessing as mp
from concurrent.futures import as_completed, ThreadPoolExecutor
from rich.progress import Progress
import threading



# Global variables
EVERY_N_MONTHS = 6
NUM_GAMES_PER_MONTH = 1000
RATING_BIN_MEANS = [1000, 1200, 1600, 1800, 2000, 2200, 2400, 2600, 2800]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)}



def download_db(date: str, output_dir: str = "lichess_db", progress = None):
    """
    Download the database for a given date and return the path to the file.
    If the file already exists, it will return the path to the file.
    Example date: "2013-01"
    """
    
    os.makedirs(output_dir, exist_ok=True)
    fname = f"lichess_db_standard_rated_{date}.pgn"
    url = f"https://database.lichess.org/standard/{fname}.zst"

    if os.path.exists(opj(output_dir, fname)):
        return opj(output_dir, fname)
    
    task = progress.add_task(f"Downloading thread: {date}", total=100)

    wget.download(url, out=output_dir, bar=lambda curr, total, width=80: progress.update(task, total=total, completed=curr))
    # print(f"\nDownloaded {fname}.zst")

    with open(opj(output_dir, f"{fname}.zst"), "rb") as compressed:
        dctx = zstandard.ZstdDecompressor()
        with open(opj(output_dir, fname), "wb") as decompressed:
            dctx.copy_stream(compressed, decompressed)
    
    # print(f"Decompressed {fname}.zst -> {fname}")
    os.remove(opj(output_dir, f"{fname}.zst"))
    # print(f"Removed {fname}.zst")
    progress.remove_task(task)

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


def filter_games(pgn_db_path: str, idx: int, start: int, end: int):
    filtered_game_offsets = []
    counter = {tempo: {mean: 0 for mean in RATING_BIN_MEANS} for tempo in TIME_CONTROL.keys()}
    # print(f"Processing {idx} from {start/1024**3:.2f} GB to {end/1024**3:.2f} GB", flush=True)
    
    with open(pgn_db_path) as pgn_db:
        pgn_db.seek(start)
        
        while pgn_db.tell() < end:
            game_headers = chess.pgn.read_headers(pgn_db)
            if game_headers is None:
                print("WTF")
                break
            
            if is_game_valid(game_headers):
                mean_rating = (int(game_headers.get("WhiteElo")) + int(game_headers.get("BlackElo"))) / 2
                bin = get_rating_bin(mean_rating)
                tempo = get_time_control(game_headers.get("TimeControl"))
                
                if tempo is not None and bin is not None:
                    if counter[tempo][bin] < NUM_GAMES_PER_MONTH:
                        counter[tempo][bin] += 1
                        filtered_game_offsets.append(pgn_db.tell())
                    else:
                        continue
                else:
                    continue

    # save to file
    fname = pgn_db_path[:-4] + f"_filtered_p{idx}.pgn"
    with open(pgn_db_path) as pgn_db:
        with open(fname, "w") as f:
            exporter = chess.pgn.FileExporter(f)
            for offset in filtered_game_offsets:
                pgn_db.seek(offset)
                game = chess.pgn.read_game(pgn_db)
                game.accept(exporter)

    # print(f"Saved {fname}")


def parallel_filter_games(pgn_db_path: str, num_processes: int):
    boundaries = divide_pgn_file(pgn_db_path, num_processes)
    # print("Filtering:", pgn_db_path.split("/")[-1])
    with mp.Pool(num_processes) as pool:
        args = [(pgn_db_path, idx, start, end) for idx, (start, end) in enumerate(boundaries)]
        pool.starmap(filter_games, args, chunksize=1)

    
    # combine the files, run cat
    # print("Combining the files")
    os.system(f"cat {pgn_db_path[:-4]}_filtered_p*.pgn > {pgn_db_path[:-4]}_filtered.pgn")
    os.system(f"rm {pgn_db_path[:-4]}_filtered_p*.pgn")
    os.system(f"rm {pgn_db_path}")


def processor_process(download_queue, num_processes):
    """Process that handles filtering downloaded files"""
    while True:
        pgn_path = download_queue.get()
        if pgn_path is None:  # Signal to stop
            print("Stopping processor")
            break

        rprint(f"[magenta]Processing[/magenta] {os.path.basename(pgn_path)}", flush=True)
        start = time.perf_counter()
        parallel_filter_games(pgn_path, num_processes)
        end = time.perf_counter()
        print(f"Time taken: {end - start:.2f} seconds")


def main(args):

    dates = []
    for year, month in product(range(2015, 2025), range(1, 13, EVERY_N_MONTHS)):
        date = f"{year}-{month:02d}"
        if os.path.exists(opj(args.output_dir, f"lichess_db_standard_rated_{date}_filtered.pgn")):
            print(f"Skipping {date} - already processed")
        else:
            dates.append(date)


    with Progress() as progress:
        download_queue = mp.Queue()
        processor = mp.Process(target=processor_process, args=(download_queue, args.num_processes), name="Processor")    
        processor.start()
 
        
        with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
            futures = []
            for date in dates:
                futures.append(executor.submit(download_db, date, args.output_dir, progress))

            for future in as_completed(futures):
                pgn_path = future.result()
                download_queue.put(pgn_path)
       
    
    # Signal that we're done downloading
    download_queue.put(None)

    # Wait for both processes to finish
    processor.join()



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db")
    arg_parser.add_argument("-p", "--num_processes", type=int, default=8)
    arg_parser.add_argument("-t", "--num_threads", type=int, default=3)
    args = arg_parser.parse_args()
    
    main(args)
