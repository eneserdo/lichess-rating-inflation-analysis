# Lichess Rating Inflation Analysis Guided by Accuracy

There is a lot of talk about rating inflation in chess. I wanted to see if this is true by analysing the data from Lichess. Although I am aware that rating has different dynamics in online and offline chess, I want to show the Lichess case. 

I will analyze the data in two ways: general trend in rating changes and rating changes of famous players.

I downloaded the Lichess PGN database from 2018 to 2024 twice a year, and filtered it according to the time period and time control. Then, I run the engine on each game and save the centipawns and finally calculated the game accuracies that is specified by Lichess.

## Reproducibility

### Requirements

For python requirements:
```bash
pip install -r requirements.txt
```

You also need to install [stockfish](https://stockfishchess.org/) in your system, and set the `STOCKFISH_PATH` in the `config.py` file. I used the version 17.

### Run

```bash
# Download and filter the database according to the config.py file.
python prepare.py -t <num_threads_for_downloading> -p <num_processes_for_filtering>

# Run the engine on each pgn file in parallel and save as evaluated pgn files
python evaluate.py -p <num_processes>

# Calculate the game accuracy and some other metrics, and save as json files per pgn file
python analyse.py 

# Plot the data
python plot.py
```


All these scripts takes a very long time to run, but they work in a persistent way, so that if you stop the process, it will resume from where it left off in the next run.

All of these scripts took me 200 hours to run.

## Download

You can download the evaluated pgn files from [here](...). If you want to use the data for your research, please cite this repository properly.