import argparse
import glob
import multiprocessing as mp
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
from os.path import join as opj
from pathlib import Path

import chess
import chess.pgn
import wget
import zstandard
from natsort import natsorted

import config as cfg
from utils import (PrintInLine, divide_pgn_file, get_rating_bin,
                   get_time_control)

NUM_PROCESSES = None
NUM_THREADS = None
STATS_TIME = None

# print lines:
#  1: "Concurently downloading and filtering games... Skipping..."
#  "Filtered {pgn_name} in {end-start:.2f}s"
#  "Decompressing {file_path.split('_')[-1].split('.')[0]}"
#  "cat'ing all parts for {pgn_db_path.split('_')[-1].split('.')[0]}"
#  "Filtered {pgn_name} in {end-start:.2f}s"


def decompress_db(file_path: str) -> str:
    """
    Decompress the file if it is not already decompressed.
    """
    msg = f"Decompressing {file_path.split('_')[-1].split('.')[0]}"
    PrintInLine.print(3+NUM_THREADS, msg)

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

    pbar = PrintInLine.get_pbar_function()
    bar_name = f"Downloading {fname.split('_')[-1].split('.')[0]}"
    wget.download(url, out=output_dir, bar=lambda curr, total, width: pbar(curr, total, bar_name, line_row))

    return opj(output_dir, fname)


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
        and (game_headers.get("TimeControl") is not None)
    )


def filter_games(pgn_db_path: str, idx: int, start: int, end: int):
    """
    Saves the game info and offsets of the valid and interested games to a file.
    Valid game: check is_game_valid()
    Interested game: check config.py
    """
    pgn_name = pgn_db_path[:-4].split("_")[-1]
    fname_to_save = pgn_db_path[:-4] + f"_filtered_p{idx}.txt"

    with open(pgn_db_path) as pgn_db, open(fname_to_save, "w") as f_out:
        pgn_db.seek(start)
        
        pbar = PrintInLine.get_pbar_function()

        curr = pgn_db.tell()
        while curr < end:
            pbar(curr - start, end - start, f"Filtering {pgn_name} p{idx:02d}", 3 + NUM_THREADS + idx)

            game_headers = chess.pgn.read_headers(pgn_db)
            if game_headers is None:
                break
            
            if is_game_valid(game_headers):
                w_name, b_name = game_headers.get("White"), game_headers.get("Black")
                w_elo, b_elo = game_headers.get('WhiteElo'), game_headers.get('BlackElo')
                result = game_headers.get('Result')
                time_control = game_headers.get('TimeControl')
                
                tempo = get_time_control(time_control)
                bin = get_rating_bin((int(w_elo) + int(b_elo)) / 2)
                
                if tempo is None or bin is None:
                    continue

                game_info = f"{w_name} {b_name} {w_elo} {b_elo} {result} {time_control} {curr}\n"
                f_out.write(game_info)

            curr = pgn_db.tell()

    return True

def extract_games(game_info_path: str, pgn_path: str):
    counter = {tempo: {mean: 0 for mean in cfg.RATING_BIN_MEANS} for tempo in cfg.TIME_CONTROL.keys()}
    counter["total"] = 0
    counter["players"] = defaultdict(int)

    pbar = PrintInLine.get_pbar_function()
    fsize = os.path.getsize(game_info_path)
    size_per_line = len(open(game_info_path).readline())
    num_lines = fsize // size_per_line
    
    with open(game_info_path) as game_info, open(pgn_path, "r") as pgn_db, open(pgn_path[:-4] + "_filtered.pgn", "w") as pgn_filtered:
        exporter = chess.pgn.FileExporter(pgn_filtered)

        for line_idx, line in enumerate(game_info):
            pbar(line_idx, num_lines, f"Extracting games from {pgn_path.split('_')[-1].split('.')[0]}", 3 + NUM_THREADS + NUM_PROCESSES + 1)

            white, black, white_elo, black_elo, result, time_control, offset = line.strip().split(" ")
            
            if counter["players"][white] >= cfg.MAX_GAMES_PER_PLAYER or counter["players"][black] >= cfg.MAX_GAMES_PER_PLAYER:
                continue
            
            tempo = get_time_control(time_control)
            bin = get_rating_bin((int(white_elo) + int(black_elo)) / 2)
            
            if tempo is None or bin is None:
                continue
            
            if counter[tempo][bin] < cfg.NUM_GAMES_PER_CONFIG:
                counter[tempo][bin] += 1
                pgn_db.seek(int(offset))
                game = chess.pgn.read_game(pgn_db)
                game.accept(exporter)
            
            if counter["total"] >= cfg.TOTAL_NUM_GAMES:
                break


def parallel_filter_games(pgn_db_path: str, num_processes: int):
    # pgn_db_path: path to the zst file
    global STATS_TIME
    STATS_TIME = time.perf_counter()
    
    
    pgn_db_path_decompressed = decompress_db(pgn_db_path)
    if os.path.exists(pgn_db_path):
        os.remove(pgn_db_path)
    pgn_db_path = pgn_db_path_decompressed

    boundaries = divide_pgn_file(pgn_db_path, num_processes)

    with mp.Pool(num_processes) as pool:
        args = [(pgn_db_path, idx, start, end) for idx, (start, end) in enumerate(boundaries)]
        results = pool.starmap(filter_games, args, chunksize=1)

    msg = f"cat'ing all parts for {pgn_db_path.split('_')[-1].split('.')[0]}"
    PrintInLine.print(3 + NUM_THREADS + NUM_PROCESSES + 1, msg)

    os.system(f"cat {pgn_db_path[:-4]}*_filtered_p*.txt > {pgn_db_path[:-4]}_filtered.txt")
    os.system(f"rm {pgn_db_path[:-4]}*_filtered_p*.txt")
    
    extract_games(pgn_db_path[:-4] + "_filtered.txt", pgn_db_path)

    os.system(f"rm {pgn_db_path[:-4]}_filtered.txt")
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
        PrintInLine.print(3 + NUM_THREADS + NUM_PROCESSES, f"Filtered {pgn_name} in {end-start:.2f}s")


def main(args):
    global NUM_PROCESSES, NUM_THREADS
    NUM_PROCESSES = args.num_processes
    NUM_THREADS = args.num_threads

    PrintInLine.reset()
    PrintInLine.print(1, "Concurently downloading and filtering games...")
    dates = []

    skip_dates = []
    for date in cfg.DATES:
        if os.path.exists(opj(args.pgn_dir, f"lichess_db_standard_rated_{date}_filtered.pgn")):
            skip_dates.append(date)
        else:
            dates.append(date)

    if skip_dates:
        print("Skipping:", ", ".join(skip_dates))

    filter_queue = mp.Queue()
    processor = mp.Process(target=processor_process, args=(filter_queue, args.num_processes), name="Processor")    
    processor.start()

    if args.num_threads > 0:
        with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
            futures = []
            for idx, date in enumerate(dates):
                futures.append(executor.submit(download_db, date, args.pgn_dir, idx))

            for future in as_completed(futures):
                pgn_path = future.result()
                filter_queue.put(pgn_path)
    else:
        not_yet_filtered = natsorted(glob.glob(opj(args.pgn_dir, "lichess_db_standard_rated_*")))
        for pgn_path in not_yet_filtered:
            if "filtered" not in pgn_path:
                if "zst" in pgn_path:
                    filter_queue.put(pgn_path)
                else:
                    filter_queue.put(pgn_path+".zst")

    print("\n")   
    # Signal that we're done downloading
    filter_queue.put(None)

    # Wait for both processes to finish
    processor.join()



if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description="Download and filter lichess games")
    arg_parser.add_argument("-p", "--pgn_dir", type=str, default="lichess_db", help="Directory to save and filter pgn files (default: lichess_db)")
    arg_parser.add_argument("-np", "--num_processes", type=int, default=6, help="Number of processes to use for filtering (default 8)")
    arg_parser.add_argument("-nt", "--num_threads", type=int, default=2, help="Number of threads to use for downloading (default 3)")
    args = arg_parser.parse_args()
    
    main(args)
