# checkers-ai

Solves a game of [checkers](https://en.wikipedia.org/wiki/English_draughts), given an initial state, using minimax w/ $\alpha-\beta$ pruning game-tree search.  

## Board Specification

Each state is a 8x8 grid representing a checkers board.

 - Black kings are denoted by "B" and Red kings are denoted by "R"
 - Black pieces are denoted by "b" and Red pieces are denoted by "r"
 - Black starts on the top of the board and Red starts at the bottom
 - Red always moves first
 - English Draught rules for moving and game wins applies


Run with:

```
python3 checkers.py --inputfile <input file> --outputfile <output file>    
```

 - input file specifies a plain-text input file to read the puzzle's initial state from
 - output file specifies a plain-text output file containing the solution found by the search algorithm

Sample usage:

```
python3 checkers.py --inputfile testcases/checkers1.txt --outputfile solutions/solution1.txt
```
