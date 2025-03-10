# A script to run the entire pipeline for a single player

import argparse
import os
import sys

import config as cfg

URL_TEMPLATE = "https://lichess.org/api/games/user/{}?rated=true&tags=true&clocks=true&evals=false&opening=false&literate=false&perfType=blitz%2Crapid%2Cclassical%2Cstandard"

def run(player: str):
    print(f"Running pipeline for {player}")
    # Download the PGN file
    url = URL_TEMPLATE.format(player)
    
    # Unzip, filter, evaluate, analse, plot 
    ...


def main(args):
    if args.username is not None:
        run(args.username)
    else:
        for player in cfg.PLAYERS:
            run(player)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", type=str, default=None, help="The Lichess username")
    args = parser.parse_args()
    main(args)