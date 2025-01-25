from collections import Counter
import copy
from itertools import product
import os
from os.path import join as opj
from pprint import pprint
from time import perf_counter
import wget
import zstandard
import chess
import chess.pgn
from rich import print as rprint
from rich.progress import Progress

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


def filter_games(pgn_db_path: str, progress: Progress):
    filtered_game_offsets = []
    counter = {
        tempo: {mean: 0 for mean in RATING_BIN_MEANS} for tempo in TIME_CONTROL.keys()
    }

    untracked_tempos = Counter()
    untracked_bins = Counter()

    with open(pgn_db_path, "rb") as f:
        num_games = sum(1 for _ in f) // 20 # assuming 20 lines per game

    task_games = progress.add_task("[green]Filtering games...", total=num_games)


    with open(pgn_db_path) as pgn_db:
        while True:
            game_headers = chess.pgn.read_headers(pgn_db)
            if game_headers is None:
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
                    if tempo is None:
                        untracked_tempos[game_headers.get("TimeControl").split("+")[0]] += 1
                    if bin is None:
                        mean_rating = round(mean_rating / 25) * 25
                        untracked_bins[mean_rating] += 1
                    continue
            
            progress.update(task_games, advance=1)

        progress.remove_task(task_games)


    rprint("\n[magenta]Filtered[/magenta]")
    pprint(counter)
    rprint("\n[magenta]untracked_tempos[/magenta]")
    pprint(untracked_tempos)
    rprint("\n[magenta]untracked_bins[/magenta]")
    pprint(untracked_bins)

    # save to file
    fname = pgn_db_path[:-4] + "_filtered.pgn"
    with open(pgn_db_path) as pgn_db:
        with open(fname, "w") as f:
            exporter = chess.pgn.FileExporter(f)
            for offset in filtered_game_offsets:
                pgn_db.seek(offset)
                game = chess.pgn.read_game(pgn_db)
                game.accept(exporter)

    os.remove(pgn_db_path)
    print(f"Removed {pgn_db_path.split('/')[-1]}")


def main():
    output_dir = "lichess_db"

    with Progress() as progress:
        dates = product(range(2015, 2025), range(1, 13, 6))
        task_dates = progress.add_task("[green]Processing...", total=len(list(copy.deepcopy(dates))))


        for year, month in dates:
            date = f"{year}-{month:02d}"
            filtered_pgn_path = opj(output_dir, f"lichess_db_standard_rated_{date}_filtered.pgn")
            pgn_path = opj(output_dir, f"lichess_db_standard_rated_{date}.pgn")
            
            if os.path.exists(filtered_pgn_path):
                print(f"Skipping {date}")
                continue
            
            print(f"Processing {date}")
            download_db(date, output_dir)
            filter_games(pgn_path, progress)

            progress.update(task_dates, advance=1)


if __name__ == "__main__":
    main()
