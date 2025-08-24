import argparse
import copy
import glob
import math
import os
import re
import sqlite3
import statistics
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

import chess.pgn
import numpy as np
from chess.engine import Cp, Mate

from utils import get_rating_bin, get_time_control

Eval = Union[Cp, Mate]


CEILING = 1000
INITIAL_CP = 15

def round_to_int(value: float) -> int:
    # to avoid bankers rounding
    return math.floor(value + 0.5)

def get_acpl(cps: List[float]) -> Tuple[float, float]:
    if len(cps) <= 1:
        raise Exception("Not enough moves to calculate ACPL")
    
    diffs = np.diff(np.array(cps))

    # TODO: mat olunca cpl de nasıl hesaplanıyor kontrol et
    # # Filter out positions where mate was found
    # mate_mask = np.abs(evals) >= 9000
    # diffs = diffs[~mate_mask[:-1]]

    # For white moves (even indices), negative diff means loss
    white_diffs = -diffs[::2]  # Negative because loss is positive
    # For black moves (odd indices), positive diff means loss
    black_diffs = diffs[1::2]

    # Only consider losses (positive values)
    white_acpl = np.mean(np.maximum(white_diffs, 0))
    black_acpl = np.mean(np.maximum(black_diffs, 0))

    return round_to_int(white_acpl), round_to_int(black_acpl)


def clip(value: int, min_val: int, max_val: int) -> int:
    return min(max(value, min_val), max_val)


# Based on https://github.com/lichess-org/scalachess/blob/42725a2e43bd3d18f0db5c2b1329edbcef457c46/core/src/main/scala/eval.scala#L79-L89
# [0, 100]
def centipawn_to_winpercent(cp: int) -> float:
    return 50 + 50 * centipawn_to_winchance(clip(cp, -CEILING, CEILING))


# [-1, 1]
def centipawn_to_winchance(cp: int) -> float:
    MULTIPLIER = -0.00368208
    value = 2 / (1 + math.exp(MULTIPLIER * cp)) - 1
    return clip(value, -1, 1)

# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L47-L55
def winpercents_to_accuracy(before_winpercent: float, after_winpercent: float) -> float:
    # Accuracy per move
    diff = after_winpercent - before_winpercent
    if diff >= 0:
        return 100.0
    raw = 103.1668100711649 * math.exp(0.04354415386753951 * diff) - 3.166924740191411
    raw += 1  # // uncertainty bonus (due to imperfect analysis)
    return clip(raw, 0, 100)


def weighted_mean(pairs: List[Tuple[float, float]]) -> Optional[float]:
    """Calculate weighted mean from (value, weight) pairs"""
    if not pairs:
        return None
    values, weights = zip(*pairs)
    return np.average(values, weights=weights)


def harmonic_mean(values: List[float]) -> Optional[float]:
    """Calculate harmonic mean"""
    if not values:
        return None
    return statistics.harmonic_mean(values)


# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L81-L115
def game_accuracy(cps: List[float]) -> Tuple[int, int]:
    """
    Calculate game accuracy for both colors
        cps: List of centipawn evaluations from white's perspective
        Returns:
            Tuple of accuracy for white and black
    """
    # I assumed start_color is always white

    # Convert centipawns to win percentages (assuming we have this function)
    all_win_percents = [centipawn_to_winpercent(cp) for cp in cps]

    # Calculate window size (10% of moves, between 2 and 8)
    window_size = min(max((len(cps) - 1) // 10, 2), 8) # -1 because of the INITIAL_CP

    # Get raw win percent values
    # all_win_percent_values = [wp.value for wp in all_win_percents]
    all_win_percent_values = all_win_percents[:]  # copy

    # Create windows for volatility calculation
    initial_windows = [all_win_percent_values[:window_size]] * (
        min(window_size, len(all_win_percent_values)) - 2
    )
    sliding_windows = [
        all_win_percent_values[i : i + window_size]
        for i in range(len(all_win_percent_values) - window_size + 1)
    ]
    windows = initial_windows + sliding_windows

    # Calculate weights using standard deviation
    weights = [
        min(max(np.std(window) if len(window) > 1 else 0, 0.5), 12)
        for window in windows
    ]

    assert len(weights) + 1 == len(all_win_percents), (
        f"{len(weights)=} + 1 != {len(all_win_percents)=}"
    )

    # Calculate weighted accuracies
    weighted_accuracies = []
    for i, ((prev_wp, next_wp), weight) in enumerate(
        zip(zip(all_win_percents[:-1], all_win_percents[1:]), weights)
    ):
        # Determine whose move it was
        color = i % 2 == 0

        # Calculate accuracy
        before = prev_wp if color else next_wp
        after = next_wp if color else prev_wp
        accuracy = winpercents_to_accuracy(before, after)

        weighted_accuracies.append(((accuracy, weight), color))

    def color_accuracy(color: bool) -> Optional[float]:
        # Get accuracies for this color
        color_pairs = [
            (acc, weight) for (acc, weight), c in weighted_accuracies if c == color
        ]
        color_values = [acc for (acc, _), c in weighted_accuracies if c == color]

        # Calculate means
        weighted = weighted_mean(color_pairs)
        harm = harmonic_mean(color_values)

        if weighted is None or harm is None:
            return None

        return (weighted + harm) / 2

    # Return accuracies for both colors
    return round_to_int(color_accuracy(True)), round_to_int(color_accuracy(False))



def detect_mate_sequence(prev_mate: Optional[int], curr_mate: Optional[int]) -> Optional[str]:
    """
    Detect mate sequence based on previous and current mate evaluations
    """
    if prev_mate is None and curr_mate is not None and curr_mate < 0: 
        return "MateCreated"
    if prev_mate is not None and prev_mate > 0 and curr_mate is None:
        return "MateLost"
    if (prev_mate is not None and curr_mate is not None and 
        prev_mate > 0 and curr_mate < 0):
        return "MateLost"
    if prev_mate is not None and curr_mate is not None:
        return "MateDelayed"
    return None


# Based on https://github.com/lichess-org/lila/blob/master/modules/tree/src/main/Advice.scala
def count_errors(evals: List[Eval], verbose: bool = False) -> Dict[str, Dict[str, int]]:
    """
    Count the number of blunders, mistakes, and inaccuracies in the game
    Blunder: 0.3 change in winpercent
    Mistake: 0.2 change in winpercent
    Inaccuracy: 0.1 change in winpercent
    """

    if len(evals) <= 1:
        raise Exception("Not enough moves to count errors")

    errors = {"white": {"blunder": 0, "mistake": 0, "inaccuracy": 0}, "black": {"blunder": 0, "mistake": 0, "inaccuracy": 0}}

    # Convert centipawns to win percentages (assuming we have this function)
    # all_win_percents = [centipawn_to_winchance(INITIAL_CP)] + [centipawn_to_winchance(cp) for cp in cps]

    for i, (prev_eval, next_eval) in enumerate(zip(evals[:-1], evals[1:])):
        color = "white" if i % 2 == 0 else "black"
        
        if isinstance(prev_eval, Cp) and isinstance(next_eval, Cp):
            prev_cp, next_cp = prev_eval.score(), next_eval.score()
            prev_wc = centipawn_to_winchance(prev_cp)
            next_wc = centipawn_to_winchance(next_cp)

            diff = prev_wc - next_wc 
            diff = diff * (-1) if color == "black" else diff
            
            if diff > 0.3:
                errors[color]["blunder"] += 1
                if verbose:
                    print(f"[CP] Blunder: {prev_cp} -> {next_cp} by {color} at {i // 2 + 1}")
            elif diff > 0.2:
                errors[color]["mistake"] += 1
                if verbose:
                    print(f"[CP] Mistake: {prev_cp} -> {next_cp} by {color} at {i // 2 + 1}")
            elif diff > 0.1:
                errors[color]["inaccuracy"] += 1
                if verbose:
                    print(f"[CP] Inaccuracy: {prev_cp} -> {next_cp} by {color} at {i // 2 + 1}")
        
        else:
            # one of the evals is a mate
            prev_cp = prev_eval.score() if isinstance(prev_eval, Cp) else None
            next_cp = next_eval.score() if isinstance(next_eval, Cp) else None
            prev_mate = prev_eval.mate() if isinstance(prev_eval, Mate) else None
            next_mate = next_eval.mate() if isinstance(next_eval, Mate) else None

            # apply inversion if black move
            if color == "black":
                prev_cp = -prev_cp if prev_cp is not None else None
                next_cp = -next_cp if next_cp is not None else None
                prev_mate = -prev_mate if prev_mate is not None else None
                next_mate = -next_mate if next_mate is not None else None
            
            sequence = detect_mate_sequence(prev_mate, next_mate)

            prev_cp_val = prev_cp if prev_cp is not None else 0
            next_cp_val = next_cp if next_cp is not None else 0
            
            if sequence == "MateCreated":
                if prev_cp_val < -999:
                    errors[color]["inaccuracy"] += 1
                    if verbose:
                        print(f"[MA] Inaccuracy: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")
                elif prev_cp_val < -700:
                    errors[color]["mistake"] += 1
                    if verbose:
                        print(f"[MA] Mistake: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")
                else:
                    errors[color]["blunder"] += 1
                    if verbose:
                        print(f"[MA] Blunder: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")

            elif sequence == "MateLost":
                if next_cp_val > 999:
                    errors[color]["inaccuracy"] += 1
                    if verbose:
                        print(f"[MA] Inaccuracy: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")
                elif next_cp_val > 700:
                    errors[color]["mistake"] += 1
                    if verbose:
                        print(f"[MA] Mistake: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")
                else:
                    errors[color]["blunder"] += 1
                    if verbose:
                        print(f"[MA] Blunder: {prev_cp_val} -> {next_cp_val} by {color} at {i // 2 + 1}, sequence: {sequence}")

    return errors


def extract_cps(game: chess.pgn.Game) -> List[float]:
    # assumes that game has at least one move
    cps = [INITIAL_CP]
    
    game = game.next() # skip the initial board (it is INITIAL_CP)

    assert game is not None, f"WTF: Game {game.headers['GameId']} has no moves"

    while True:

        eval = game.eval().white()
        if isinstance(eval, chess.engine.Cp):
            score = clip(eval.score(), -CEILING, CEILING)

        elif isinstance(eval, chess.engine.Mate):
            score = CEILING if eval.mate() > 0 else -CEILING
        else:
            raise ValueError(f"Unknown eval type: {type(eval)}")
        
        assert score is not None, f"WTF: Game {game.headers['GameId']} has no score"
        cps.append(score)

        if game.is_end():
            break

        game = game.next()
    

    return cps

def extract_evals(game: chess.pgn.Game) -> List[Eval]:
    # assumes that game has at least one move
    evals = [Cp(INITIAL_CP)]
    
    game = game.next() # skip the initial board (it is INITIAL_CP)

    assert game is not None, f"WTF: Game {game.headers['GameId']} has no moves"

    counter = 0
    while True:
        if len(game.variations) > 1:
            counter += 1

        eval = game.eval().white()
        evals.append(eval)


        if game.is_end():
            break

        game = game.next()
    
    print(f"Counter: {counter}")
    return evals

def evals_to_cps(evals: List[Eval]) -> List[float]:
    cps = []

    for eval in evals:
        if isinstance(eval, Cp):
            cps.append(clip(eval.score(), -CEILING, CEILING))
        elif isinstance(eval, Mate):
            cps.append(CEILING if eval.mate() > 0 else -CEILING)
        else:
            raise ValueError(f"Unknown eval type: {type(eval)}")

    return cps



def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Extract date from PGN filename in format YYYY-MM
    Expected format: lichess_db_standard_rated_YYYY-MM_*.pgn
    """
    match = re.search(r'(\d{4}-\d{2})', filename)
    return match.group(1) if match else None


def extract_game_id_from_site(site: str) -> Optional[str]:
    """
    Extract game ID from Site field
    Expected format: [Site "https://lichess.org/GAME_ID"]
    """
    if not site:
        return None
    
    # Extract the part after "lichess.org/"
    match = re.search(r'lichess\.org/([a-zA-Z0-9]+)', site)
    return match.group(1) if match else None


def check_for_duplicates_in_database(conn: sqlite3.Connection, date: str) -> Dict[str, int]:
    """
    Check for existing games from the same date in the database
    Returns statistics about existing games
    """
    cursor = conn.cursor()
    
    # Count total games for this date
    cursor.execute("SELECT COUNT(*) FROM game_metrics WHERE date = ?", (date,))
    total_games = cursor.fetchone()[0]
    
    # Count by tempo
    cursor.execute("""
        SELECT tempo, COUNT(*) 
        FROM game_metrics 
        WHERE date = ? 
        GROUP BY tempo
    """, (date,))
    tempo_counts = dict(cursor.fetchall())
    
    # Count by rating bin
    cursor.execute("""
        SELECT bin, COUNT(*) 
        FROM game_metrics 
        WHERE date = ? 
        GROUP BY bin
    """, (date,))
    bin_counts = dict(cursor.fetchall())
    
    return {
        'total': total_games,
        'tempo_counts': tempo_counts,
        'bin_counts': bin_counts
    }


def create_database(db_path: str = "chess_metrics.db") -> sqlite3.Connection:
    """
    Create SQLite database with the specified schema
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            game_id TEXT,
            w_elo INTEGER NOT NULL,
            b_elo INTEGER NOT NULL,
            bin TEXT NOT NULL,
            game_result TEXT NOT NULL,
            time_control TEXT NOT NULL,
            tempo TEXT,
            w_acpl REAL,
            w_accuracy REAL,
            w_inaccuracies INTEGER,
            w_mistakes INTEGER,
            w_blunders INTEGER,
            b_acpl REAL,
            b_accuracy REAL,
            b_inaccuracies INTEGER,
            b_mistakes INTEGER,
            b_blunders INTEGER,
            UNIQUE(date, game_id, w_elo, b_elo, game_result, time_control, w_acpl, b_acpl)
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON game_metrics(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_id ON game_metrics(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bin ON game_metrics(bin)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tempo ON game_metrics(tempo)')
    
    conn.commit()
    return conn


def extract_game_metrics(game: chess.pgn.Game, date: str) -> Optional[Dict]:
    """
    Extract metrics from a single game and return as dictionary
    Returns None if the game cannot be processed
    """
    w_elo, b_elo = game.headers.get('WhiteElo'), game.headers.get('BlackElo')
        
    w_elo, b_elo = int(w_elo), int(b_elo)
        
    bin_rating = get_rating_bin((w_elo + b_elo) / 2)
        
    result = game.headers.get('Result')
    time_control = game.headers.get('TimeControl')
    tempo = get_time_control(time_control)
    
    # Extract game ID from Site field
    site = game.headers.get('Site')
    game_id = extract_game_id_from_site(site)

    evals = extract_evals(game)
    
    cps = evals_to_cps(evals)
    w_acpl, b_acpl = get_acpl(cps)
    white_accuracy, black_accuracy = game_accuracy(cps)
    errors = count_errors(evals)
    
    return {
        'date': date,
        'game_id': game_id,
        'w_elo': w_elo,
        'b_elo': b_elo,
        'bin': bin_rating,
        'game_result': result,
        'time_control': time_control,
        'tempo': tempo,
        'w_acpl': w_acpl,
        'w_accuracy': white_accuracy,
        'w_inaccuracies': errors['white']['inaccuracy'],
        'w_mistakes': errors['white']['mistake'],
        'w_blunders': errors['white']['blunder'],
        'b_acpl': b_acpl,
        'b_accuracy': black_accuracy,
        'b_inaccuracies': errors['black']['inaccuracy'],
        'b_mistakes': errors['black']['mistake'],
        'b_blunders': errors['black']['blunder']
    }


def insert_metrics_batch(conn: sqlite3.Connection, metrics_batch: List[Dict], batch_size: int = 1000):
    """
    Insert a batch of metrics into the database
    Returns the number of duplicates found
    """
    cursor = conn.cursor()
    
    insert_query = '''
        INSERT OR IGNORE INTO game_metrics (
            date, game_id, w_elo, b_elo, bin, game_result, time_control, tempo,
            w_acpl, w_accuracy, w_inaccuracies, w_mistakes, w_blunders,
            b_acpl, b_accuracy, b_inaccuracies, b_mistakes, b_blunders
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    total_duplicates = 0
    
    for i in range(0, len(metrics_batch), batch_size):
        batch = metrics_batch[i:i + batch_size]
        values = [
            (
                m['date'], m['game_id'], m['w_elo'], m['b_elo'], m['bin'], m['game_result'],
                m['time_control'], m['tempo'], m['w_acpl'], m['w_accuracy'],
                m['w_inaccuracies'], m['w_mistakes'], m['w_blunders'],
                m['b_acpl'], m['b_accuracy'], m['b_inaccuracies'],
                m['b_mistakes'], m['b_blunders']
            )
            for m in batch
        ]
        
        # Get count before insertion
        cursor.execute("SELECT COUNT(*) FROM game_metrics")
        count_before = cursor.fetchone()[0]
        
        cursor.executemany(insert_query, values)
        conn.commit()
        
        # Get count after insertion
        cursor.execute("SELECT COUNT(*) FROM game_metrics")
        count_after = cursor.fetchone()[0]
        
        # Calculate how many were actually inserted vs attempted
        attempted = len(batch)
        actually_inserted = count_after - count_before
        duplicates_in_batch = attempted - actually_inserted
        total_duplicates += duplicates_in_batch
        
        if duplicates_in_batch > 0:
            print(f"⚠️  WARNING: Found {duplicates_in_batch} duplicate games in batch (attempted: {attempted}, inserted: {actually_inserted})")
        else:
            print(f"Inserted batch of {actually_inserted} games")
    
    return total_duplicates


def extract_metrics_from_file(pgn_file_path: str, date: str) -> Generator[Dict, None, None]:
    """
    Extract metrics from a single PGN file
    Yields individual game metrics as dictionaries
    """
    games_processed = 0
    games_extracted = 0
    seen_games = set()  # Track potential duplicates within the file
    duplicates_in_file = 0
    
    print(f"Processing {pgn_file_path} for date {date}")
    
    with open(pgn_file_path, "r") as pgn_file:
        while True:
            # try:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
                
            games_processed += 1
            
            # Print progress every 100 games
            if games_processed % 100 == 0:
                print(f"  Processed {games_processed} games, extracted {games_extracted} valid games")
            
            metrics = extract_game_metrics(game, date)
            if metrics is not None:
                # Create a signature for duplicate detection within the file
                # Use game_id if available, otherwise fall back to other fields
                if metrics['game_id']:
                    game_signature = metrics['game_id']
                else:
                    game_signature = (
                        metrics['w_elo'], metrics['b_elo'], metrics['game_result'],
                        metrics['time_control'], round(metrics['w_acpl'], 2), round(metrics['b_acpl'], 2)
                    )
                
                if game_signature in seen_games:
                    duplicates_in_file += 1
                    if duplicates_in_file <= 5:  # Only show first 5 warnings to avoid spam
                        game_id_info = f"ID={metrics['game_id']}" if metrics['game_id'] else f"W{metrics['w_elo']} vs B{metrics['b_elo']}"
                        print(f"⚠️  Potential duplicate within file: {game_id_info}, result={metrics['game_result']}")
                else:
                    seen_games.add(game_signature)
                
                games_extracted += 1
                yield metrics
            else:
                print(f"Error processing game {games_processed}: {metrics}")
                
            # except Exception as e:
            #     print(f"Error reading game {games_processed}: {e}")
            #     continue
    
    completion_msg = f"Completed {pgn_file_path}: {games_processed} games processed, {games_extracted} valid games extracted"
    if duplicates_in_file > 0:
        completion_msg += f", {duplicates_in_file} potential intra-file duplicates detected"
    print(completion_msg)


def process_all_pgn_files(pgn_dir: str, db_path: str = "chess_metrics.db"):
    """
    Process all PGN files in the specified directories and store metrics in database
    """
    if os.path.exists(db_path):
        print(f"Database {db_path} already exists!")
        return
    
    conn = create_database(db_path)
    
    # Find all evaluated PGN files
    pgn_files = glob.glob(os.path.join(pgn_dir, "*_evaluated.pgn"))
    
    if not pgn_files:
        print("No evaluated PGN files found!")
        return
    
    pgn_files.sort()  # Process in chronological order
    print(f"Found {len(pgn_files)} PGN files to process")
    
    total_games_inserted = 0
    
    for pgn_file in pgn_files:
        date = extract_date_from_filename(pgn_file)
        if date is None:
            print(f"Could not extract date from filename: {pgn_file}")
            continue
        
        # Check if this file has already been processed
        duplicate_stats = check_for_duplicates_in_database(conn, date)
        
        if duplicate_stats['total'] > 0:
            print(f"⚠️  WARNING: Date {date} already has {duplicate_stats['total']} games in database!")
            print(f"   📊 Breakdown by tempo: {duplicate_stats['tempo_counts']}")
            print(f"   📊 Breakdown by rating bin: {duplicate_stats['bin_counts']}")
            print("   🚫 Skipping file to avoid duplicates...")
            continue
        
        # Extract metrics from this file
        metrics_batch = []
        batch_size = 1000
        file_duplicates = 0
        file_games_inserted = 0
        
        for metrics in extract_metrics_from_file(pgn_file, date):
            metrics_batch.append(metrics)
            
            # Insert in batches to avoid memory issues
            if len(metrics_batch) >= batch_size:
                duplicates = insert_metrics_batch(conn, metrics_batch, batch_size)
                file_duplicates += duplicates
                file_games_inserted += len(metrics_batch) - duplicates
                total_games_inserted += len(metrics_batch) - duplicates
                metrics_batch = []
        
        # Insert remaining metrics
        if metrics_batch:
            duplicates = insert_metrics_batch(conn, metrics_batch, batch_size)
            file_duplicates += duplicates
            file_games_inserted += len(metrics_batch) - duplicates
            total_games_inserted += len(metrics_batch) - duplicates
        
        # Report file-level statistics
        if file_duplicates > 0:
            print(f"📊 File {os.path.basename(pgn_file)} completed: {file_games_inserted} games inserted, {file_duplicates} duplicates found")
        else:
            print(f"✅ File {os.path.basename(pgn_file)} completed: {file_games_inserted} games inserted, no duplicates")
    
    # Final summary with duplicate statistics
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM game_metrics")
    final_total = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'='*60}")
    print("DATABASE PROCESSING COMPLETE!")
    print(f"{'='*60}")
    print(f"📈 Total games successfully inserted: {total_games_inserted}")
    print(f"📊 Total games in database: {final_total}")
    print(f"💾 Database saved as: {db_path}")
    
    if final_total != total_games_inserted:
        existing_games = final_total - total_games_inserted
        print(f"ℹ️  Note: Database contains {existing_games} games from previous runs")
    
    print(f"{'='*60}")


def print_database_stats(db_path: str = "chess_metrics.db"):
    """
    Print statistics about the database contents
    """
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total games
    cursor.execute("SELECT COUNT(*) FROM game_metrics")
    total_games = cursor.fetchone()[0]
    print(f"Total games in database: {total_games}")
    
    # Games by date
    cursor.execute("SELECT date, COUNT(*) FROM game_metrics GROUP BY date ORDER BY date")
    date_counts = cursor.fetchall()
    print("\nGames by date:")
    for date, count in date_counts:
        print(f"  {date}: {count} games")
    
    # Games by rating bin
    cursor.execute("SELECT bin, COUNT(*) FROM game_metrics GROUP BY bin ORDER BY bin")
    bin_counts = cursor.fetchall()
    print("\nGames by rating bin:")
    for bin_rating, count in bin_counts:
        print(f"  {bin_rating}: {count} games")
    
    # Games by tempo
    cursor.execute("SELECT tempo, COUNT(*) FROM game_metrics GROUP BY tempo ORDER BY tempo")
    tempo_counts = cursor.fetchall()
    print("\nGames by tempo:")
    for tempo, count in tempo_counts:
        print(f"  {tempo}: {count} games")
    
    # Game ID statistics
    cursor.execute("SELECT COUNT(*) FROM game_metrics WHERE game_id IS NOT NULL")
    games_with_id = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM game_metrics WHERE game_id IS NULL")
    games_without_id = cursor.fetchone()[0]
    print("\nGame ID statistics:")
    print(f"  Games with ID: {games_with_id}")
    print(f"  Games without ID: {games_without_id}")
    
    conn.close()


def main(args):
    
    if args.stats:
        print_database_stats(args.db_path)
        return
    
    process_all_pgn_files(args.pgn_dir, args.db_path)
    print_database_stats(args.db_path)


if __name__ == "__main__":
    for i in range(7, 8):
        with open(f"tests/sample_pgns/g{i}.pgn", "r") as f:
            game = chess.pgn.read_game(f)
            evals = extract_evals(game)
            cps = evals_to_cps(evals)
            w_acpl, b_acpl = get_acpl(cps)
            print("w_acpl: ", w_acpl, "b_acpl: ", b_acpl)
            print("game_accuracy: ", game_accuracy(cps))
            from pprint import pprint
            pprint(count_errors(evals, verbose=True))
            print("-"*100)

            # game = chess.pgn.read_game(f)
            # evals = extract_evals(game)
            # for eval in evals:
            #     if isinstance(eval, Cp):
            #         print(f"Cp({eval.score()})", end=", ")
            #     elif isinstance(eval, Mate):
            #         print(f"Mate({eval.mate()})", end=", ")
            #     else:
            #         raise ValueError(f"Unknown eval type: {type(eval)}")
            # print()


            # cps = evals_to_cps(evals)
            # w_acpl, b_acpl = get_acpl(cps)
            # print("w_acpl: ", w_acpl, "b_acpl: ", b_acpl)
            # print("game_accuracy: ", game_accuracy(cps))
            # from pprint import pprint
            # pprint(count_errors(evals))
            # print("-"*100)

# if __name__ == "__main__":
#     arg_parser = argparse.ArgumentParser(description="Analyse PGN files and store metrics in database")
#     arg_parser.add_argument("-p", "--pgn_dir", type=str, default="temp_db", help="Primary directory to process PGN files")
#     arg_parser.add_argument("--db-path", type=str, default="chess_metrics.db", help="Path to SQLite database file")
#     arg_parser.add_argument("-s", "--stats", action="store_true", help="Print database statistics")
    
#     args = arg_parser.parse_args()
#     main(args)

# TODO: error sayılarını kaynaktan tekrar kontrol et
# TODO: mateadvice ile erorr hesabını yap