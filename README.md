# My Great Plan

## Analysis 

### For general trend

- For every 6 months from 2015-01 to 2025-01:
    - Download the database (`download_db`)
    - Remove uninteresting games
    - Delete the database

- For each database:
    - Run the engine on each game in parallel save centipawns and accuracy

- Create nested dict for accuracy:
    - Time (6 months)
    - Time control (blitz, rapid)
    - Rating (1000±50, 1200±50, ..., 2800±50)

### For famous players

- For each player:
    - Get their pgns
    - Run the engine on each game in parallel save centipawns and accuracy

# Lichess Rating Inflation Analysis

The details are explained in [here](...).


## Reproducibility

### Requirements

For python requirements:
```bash
pip install -r requirements.txt
```

You also need to install `stockfish` in your system, and set the `STOCKFISH_PATH` in the `config.py` file.

### Run

```bash
# Download and filter the database according to the configuration
python prepare.py -t <num_threads_for_downloading> -p <num_processes_for_filtering>

# Run the engine on each game in parallel, and save centipawns and accuracies
python analyze.py

# Plot the data
python plot.py
```
All these scripts takes a very long time to run, but they work in a persistent way, so that if you stop the process, it will resume from where it left off in the next run.

All of the process took me 200 hours overall.

## Download

You can download the processed data from [here](...). Please cite this repository properly.