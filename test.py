import asyncio
from functools import partial
import os
import time

import chess
import chess.engine
import chess.pgn

from main import eval_pgn
import multiprocessing as mp


def process_file_part(file_path, start, end, condition):
    """
    Read and process a part of the file between start and end positions.
    """
    with open(file_path, 'r') as f:
        f.seek(start)  # Move to the start position
        
        if start != 0:
            f.readline()  # Skip the incomplete line (if any)
        
        lines = []
        while f.tell() < end:
            line = f.readline()
            if not line:  # End of file
                break
            if condition(line):  # Apply condition
                lines.append(line)
    
    return lines

def divide_file(file_path, num_processes):
    """
    Divide the file into approximately equal parts for each process.
    """
    file_size = os.path.getsize(file_path)
    chunk_size = file_size // num_processes
    boundaries = [(i * chunk_size, (i + 1) * chunk_size) for i in range(num_processes)]
    boundaries[-1] = (boundaries[-1][0], file_size)  # Ensure the last chunk covers the end
    return boundaries

def parallel_file_processing(file_path, output_path, condition, num_processes=4):
    """
    Process a file in parallel using multiple pointers.
    """
    # Divide the file into chunks
    boundaries = divide_file(file_path, num_processes)

    # Create a pool of processes
    pool = mp.Pool(num_processes)
    results = []
    with mp.Pool(num_processes) as pool:
        for start, end in boundaries:
            result = pool.apply_async(process_file_part, args=(file_path, start, end, condition))
            results.append(result)

    pool.close()
    pool.join()

    # Collect results and write to output file
    with open(output_path, 'w') as out_file:
        for result in results:
            out_file.writelines(result.get())

if __name__ == '__main__':
    def my_condition(line):
        # Example: Keep lines containing the word "filter"
        return "filter" in line

    input_file = "large_input.txt"
    output_file = "filtered_output.txt"
    parallel_file_processing(input_file, output_file, my_condition)

            
