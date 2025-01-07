## Copyright (C) 2025, Nicholas Carlini <nicholas@carlini.com>.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Any

from compiler import re_compile
from chess_engine import make_reply_move

def escape_non_ascii(match):
    return '\\u{:04x}'.format(ord(match.group()))

def write_js_output(args: List[Tuple[str, List[Tuple[str, str]]]], outfile: str):
    """Write JavaScript format output"""
    state = '''  ╔═════════════════╗
8 ║ ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜ ║
7 ║ ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟ ║
6 ║                 ║
5 ║                 ║
4 ║                 ║
3 ║                 ║
2 ║ ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙ ║
1 ║ ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖ ║
  ╚═════════════════╝
    a b c d e f g h

Move notation: [src][dest] (e.g. e2e4) or 'q' to quit
[Castling Rights: KQkq, En Passant: -]
Enter Your Move: '''
    
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(f'let initialState = {json.dumps(state)};\n')
        f.write('let regexOperation = [\n')
        
        for op, regexs in args:
            for pattern, repl in regexs:
                repl = re.sub(r'\\(\d+)', r'$\1', repl)
            
                repl = re.sub(r'\\g<(\d+)>', r'$\1', repl)
            
                # Handle pattern escaping
                pattern = pattern.replace("\n", "\\n").replace("/",r"\/")
                if pattern[0] == '^':
                    flags = "/g"
                else:
                    flags = "/gm"
                content = ("['" + str(op).replace("'",'"') + "', /"+pattern+flags + ", " + json.dumps(repl).replace(r"\\n", r"\n") + "],")
                converted = re.sub(r'[^\x00-\x7F]', escape_non_ascii, content)

                f.write(converted + '\n')
        
        f.write(']\n')

def write_json_output(args: List[Tuple[str, List[Tuple[str, str]]]], outfile: str):
    """Write JSON format output"""
    operations = []

    operations.append(['^$', '<'])
    
    for op, regexs in args:
        for pattern, repl in regexs:
            regex_op = [pattern,
                        repl,
                        ]
            operations.append(regex_op)

    operations.append(['^<$', '''  ╔═════════════════╗
8 ║ ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜ ║
7 ║ ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟ ║
6 ║                 ║
5 ║                 ║
4 ║                 ║
3 ║                 ║
2 ║ ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙ ║
1 ║ ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖ ║
  ╚═════════════════╝
    a b c d e f g h

Move notation: [src][dest] (e.g. e2e4) or 'q' to quit
[Castling Rights: KQkq, En Passant: -]
Enter Your Move: '''])            
    
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(operations, f, indent=2, ensure_ascii=False)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate regex patterns file')
    parser.add_argument('outfile', help='Output file path (.js or .json)')
    args = parser.parse_args()
    
    # Generate the regex tree
    regex_args = re_compile(lambda x: make_reply_move(x))
    
    # Determine output format based on file extension
    file_ext = Path(args.outfile).suffix.lower()
    
    if file_ext == '.js':
        write_js_output(regex_args, args.outfile)
    elif file_ext == '.json':
        write_json_output(regex_args, args.outfile)
    else:
        print(f"Error: Unsupported file extension '{file_ext}'. Use .js or .json", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
