# Evaluation Checkpoint System

This document explains the checkpoint functionality added to the evaluation script to allow resuming interrupted evaluations.

## Overview

The evaluation process can be very slow, especially for large PGN files. If the process is interrupted (due to system crash, power outage, or manual termination), you can now resume from where it left off without losing progress.

## How It Works

The checkpoint system uses a temporary directory to store metadata about the evaluation progress:

1. **File-level checkpoints**: Track which processes have completed for each PGN file
2. **Process-level checkpoints**: Track the current position and number of games evaluated for each process
3. **Automatic cleanup**: Checkpoint files are automatically removed when evaluation completes successfully

## Usage

### Basic Usage

```bash
# Start evaluation (will create checkpoints automatically)
python evaluate.py -p lichess_db -np 8

# If interrupted, simply run the same command again
python evaluate.py -p lichess_db -np 8
```

### Check Progress

```bash
# Check progress of all files being evaluated
python evaluate.py -p lichess_db -cp
```

### Custom Temp Directory

```bash
# Use a custom directory for checkpoint files
python evaluate.py -p lichess_db -np 8 -td /path/to/temp/dir
```

## Command Line Arguments

- `-p, --pgn_dir`: Directory containing PGN files (default: "lichess_db")
- `-np, --num_processes`: Number of processes to use (default: 8)
- `-t, --threads`: Number of threads for Stockfish (default: None)
- `-hs, --hash`: Hash size for Stockfish (default: None)
- `-td, --temp_dir`: Temporary directory for checkpoints (default: "temp_eval_checkpoints")
- `-cp, --check_progress`: Check evaluation progress for all files

## Checkpoint Files

The system creates two types of checkpoint files:

1. **File checkpoints** (`*_checkpoint.json`): Track completed processes for each PGN file
2. **Process checkpoints** (`*_p*_checkpoint.json`): Track individual process progress

These files are stored in the temp directory and are automatically cleaned up when evaluation completes. All checkpoint files use JSON format for human readability and portability.

## Recovery Scenarios

### Scenario 1: Process Interruption
If the evaluation process is interrupted (Ctrl+C, system crash, etc.), simply run the same command again. The system will:
- Detect existing checkpoints
- Skip completed processes
- Resume from the last saved position for incomplete processes

### Scenario 2: Partial File Corruption
If a partial evaluated file is corrupted, the system will:
- Detect the corruption through checkpoint validation
- Restart the affected process from the beginning
- Continue with other processes normally

### Scenario 3: Manual Cleanup
If you want to restart evaluation from scratch:
```bash
# Remove checkpoint directory
rm -rf temp_eval_checkpoints

# Run evaluation again
python evaluate.py -p lichess_db -np 8
```

## Performance Considerations

- Checkpoints are saved after each game evaluation (minimal overhead)
- All checkpoint files use JSON format for simplicity and portability
- Checkpoint files are small and don't impact performance significantly
- JSON format allows easy inspection and debugging of checkpoint data

## Troubleshooting

### Checkpoint Directory Issues
If you encounter permission issues with the temp directory:
```bash
# Use a different directory
python evaluate.py -p lichess_db -np 8 -td /tmp/chess_checkpoints
```

### Corrupted Checkpoints
If checkpoint files become corrupted:
```bash
# Remove the specific checkpoint file or entire directory
rm -rf temp_eval_checkpoints
```

### Disk Space Issues
Monitor disk space usage:
```bash
# Check temp directory size
du -sh temp_eval_checkpoints
```

## Example Output

When checking progress:
```
Evaluation Progress for: lichess_db_standard_rated_2015-01_filtered.pgn
Completed processes: 5/8
Progress: 62.5%
Completed process indices: [0, 1, 2, 3, 4]
Process 5: 15 games evaluated
Process 6: 0 games evaluated
Process 7: 0 games evaluated
```

This shows that processes 0-4 have completed, process 5 has evaluated 15 games, and processes 6-7 haven't started yet. 