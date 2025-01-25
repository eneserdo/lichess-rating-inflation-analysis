from collections import Counter
import copy
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
from rich.progress import Progress
import multiprocessing as mp

# Global variables
EVERY_N_MONTHS = 6
NUM_GAMES_PER_MONTH = 1000
RATING_BIN_MEANS = [1000, 1200, 1600, 1800, 2000, 2200, 2400, 2600, 2800]
RATING_BINS = [(mean - 50, mean + 50) for mean in RATING_BIN_MEANS]
TIME_CONTROL = {"blitz": (180, 300), "rapid": (600, 900)}


def download_db(date: str, output_dir: str = "lichess_db"):
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
    
    wget.download(url, out=output_dir)
    print(f"Downloaded {fname}.zst")

    with open(opj(output_dir, f"{fname}.zst"), "rb") as compressed:
        dctx = zstandard.ZstdDecompressor()
        with open(opj(output_dir, fname), "wb") as decompressed:
            dctx.copy_stream(compressed, decompressed)
    
    print(f"Decompressed {fname}.zst -> {fname}")
    os.remove(opj(output_dir, f"{fname}.zst"))
    print(f"Removed {fname}.zst")

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
    print(f"Processing {idx} from {start} to {end}", flush=True)
    
    i = 0
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

    print(f"Saved {fname}")


def parallel_filter_games(pgn_db_path: str, num_processes: int):
    
    boundaries = divide_pgn_file(pgn_db_path, num_processes)
    with mp.Pool(num_processes) as pool:
        args = [(pgn_db_path, idx, start, end) for idx, (start, end) in enumerate(boundaries)]
        pool.starmap(filter_games, args)

    
    # combine the files, run cat
    print("Combining the files")
    os.system(f"cat {pgn_db_path[:-4]}_filtered_p*.pgn > {pgn_db_path[:-4]}_filtered.pgn")
    os.system(f"rm {pgn_db_path[:-4]}_filtered_p*.pgn")
    os.system(f"rm {pgn_db_path}")


def main():
    output_dir = "lichess_db"

    num_processes = int(sys.argv[1]) if len(sys.argv) > 1 else 8

    # dates = product(range(2015, 2025), range(1, 13, 6))
    dates = [("2015", 1)]

    for year, month in dates:
        date = f"{year}-{month:02d}"
        filtered_pgn_path = opj(output_dir, f"lichess_db_standard_rated_{date}_filtered.pgn")
        pgn_path = opj(output_dir, f"lichess_db_standard_rated_{date}.pgn")
        
        if os.path.exists(filtered_pgn_path):
            print(f"Skipping {date}")
            continue
        
        print(f"Processing {date}")
        download_db(date, output_dir)
        # filter_games(pgn_path, progress)
        start = time.perf_counter()
        parallel_filter_games(pgn_path, num_processes)
        end = time.perf_counter()
        print(f"Time taken: {end - start} seconds")



if __name__ == "__main__":
    main()
