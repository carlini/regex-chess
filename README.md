# RegexChess

RegexChess is a complete chess engine that plays moves making regular expression transforms
to a given board state. It implements a 2-ply minimax search algorithm and generates moves
in about 5-10 seconds.

## I just want to play a game

You probably don't. It's really not good. But [here](https://nicholas.carlini.com/writing/2025/regex-chess.html) is a link to a JavaScript frontend that
plays the engine. If you want to run it on your own machine, all you have to do is clone this
project and then run `python3 main.py`. It's actually a very simple file:

```python
import readline
import json
import re

state = ''
regexs = json.load(open("regex-chess.json"))
while 'Game over' not in state:
    for pattern, repl in regexs:
        state = re.sub(pattern, repl, state)
    print(state, end="")
    state += input() + "\n"
```

## How does it work?

It's complicated. See [this article on my website](https://nicholas.carlini.com/writing/2025/regex-chess.html) for a long writeup.


## License

GPL v3