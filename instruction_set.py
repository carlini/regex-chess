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

import re
import sys
import json
import time

INSTRUCTIONS = {}

def instruction(func):
    INSTRUCTIONS[func.__name__] = func
    return func


@instruction
def lookup(variable):
    # Find the variable's value and push it onto the stack
    return [(r"(%%\n#stack:)([^%]*\n#"+variable+": )([^#%]*)\n",
            r"\1\n\3\2\3\n")]
    # Groups:
    # 1: (%%\n#stack:) - Matches from %% to #stack:
    # 2: ([^%]*\n#"+variable+": ) - Matches from stack to the variable definition
    # 3: ([^#]*) - Captures the variable's value
    # Result: Keeps original variable and also pushes its value onto stack

@instruction
def indirect_lookup():
    return [
        # Look up the value of the variable whose name is on top of stack
        # and replace the name with the value
        (r"(%%\n#stack:\n)([^\n]+)\n([^%]*#\2: )([^#%\n]*)",
         r"\1\4\n\3\4")
    ]

@instruction
def indirect_assign():
    # Pop top two stack values and use them for variable assignment
    # First pop is the value to assign
    # Second pop is the variable name to assign to
    return [
        # Try to update existing variable and mark thread if successful
        (r"(%%)[^%]*#stack:\n([^\n]*)\n([^\n]*)\n([^%]*#\3: )[^\n]*",
         r"\1`\n#stack:\n\4\2"),
         
        # If no backtick (no existing variable), create new one at end of thread
        (r"(%%)([^`][^%]*#stack:\n)([^\n]*)\n([^\n]*)\n([^%]*$)",
         r"\1`\2\5#\4: \3\n"),
         
        # Clean up backtick
        (r"%%`",
         r"%%")
    ]
    # Groups for update case:
    # 1: %% - Thread start
    # 2: Value to assign
    # 3: Variable name
    # 4: Existing variable declaration
    
    # Groups for create case:
    # 1: %% - Thread start
    # 2: Everything through stack:
    # 3: Value to assign
    # 4: Variable name
    # 5: Rest of thread content

@instruction
def assign_pop(varname):
    return [
        # Try to update existing variable and mark thread if successful
        (r"(%%)\n#stack:\n([^\n]*)\n([^%]*#" + varname + r": )[^\n]*",
         r"\1`\n#stack:\n\3\2"),
         
        # If no backtick (no existing variable), create new one at end of thread
        (r"(%%)([^`]\n?#stack:\n)([^\n%]*)\n([^%]*)",
         r"\1`\2\4#" + varname + r": \3\n"),
         
        # Clean up backtick
        (r"%%`",
         r"%%")
    ]

@instruction
def is_stack_empty():
    """Check if the stack is empty, pushing True/False as result"""
    return [
        # If not empty, mark with backtick and False
        (r"(%%\n#stack:\n)([^#%])", r"\1`False\n\2"),
        
        # If no backtick (so must be empty), push True
        (r"(%%\n#stack:\n)([^`])", r"\1True\n\2"),

        # If no backtick (so must be empty), push True
        (r"(%%\n#stack:\n)$", r"\1True\n"),
        
        # Clean up backtick
        (r"`", r"")
    ]
@instruction
def push(const):
    if type(const) == int:
        const = f"int{const:010b}"
    # Push a constant value onto the stack
    return [(r"(%%\n#stack:\n)",  # Find the stack position
             r"\g<1>"+const+r"\n")]     # Add the constant after #stack:
    # Groups:
    # 1: Everything from %% through #stack:\n
    # Result: Appends the constant value to the stack

@instruction
def pop():
    # Remove top value from stack
    return [(r"(%%\n#stack:\n)([^\n]*)\n",  # Match stack header and top value
            r"\1")]                             # Keep only the header
    # Groups:
    # 1: (%%\n#stack:\n) - Matches from %% through #stack:\n
    # 2: ([^\n]*)\n - Captures the top stack value
    # Result: Removes the top stack value

@instruction
def peek():
    return []
    
@instruction
def dup():
    # Duplicate top value on stack
    return [(r"(%%\n#stack:\n)([^\n]*)\n",  # Match stack header and top value
            r"\1\2\n\2\n")]                    # Duplicate the top value
    # Groups:
    # 1: (%%\n#stack:\n) - Matches from %% through #stack:\n
    # 2: ([^\n]*) - Captures the top stack value
    # Result: Duplicates the top stack value

@instruction
def swap():
    # Swap top two values on stack
    return [(r"(%%\n#stack:\n)([^\n]*)\n([^\n]*)\n",  # Match top two values
            r"\1\3\n\2\n")]                               # Reverse their order
    # Groups:
    # 1: (%%\n#stack:\n) - Matches from %% through #stack:\n
    # 2: ([^\n]*) - Captures the top stack value
    # 3: ([^\n]*) - Captures the second stack value
    # Result: Swaps the order of the top two values

@instruction
def eq():
    return [
        # Compare top two stack values for equality
        # If equal: Replace with True (marked with backtick)
        (r"(%%\n#stack:\n)([^\n]*)\n\2\n",  # Match two identical values
         r"\1`True\n"),                        # Replace with marked True
        
        # If not equal (and not already marked): Replace with False
        (r"(%%\n#stack:\n)([^`][^\n]*)\n([^\n]*)\n",  # Match any two values
         r"\1False\n"),                                  # Replace with False
        
        # Remove the backtick marker from True results
        (r"`",
         r"")
    ]
    # Uses backtick to prevent False case from overwriting True case

@instruction
def isany(options):
    """
    Check if the top value on the stack matches any of the given options.
    Returns True if there's a match, False otherwise.
    Uses backtick (`) to mark successful matches so they're not overwritten.
    
    Args:
        options: List of strings to check against the top of stack
    """
    # Create a single pattern with all options joined by |
    options_pattern = "|".join(re.escape(opt) for opt in options)
    
    return [
        # If top of stack matches any option, mark as True with `
        (fr"(%%\n#stack:\n)({options_pattern})\n",
         r"\1`True\n"),
        
        # If no match (no backtick), replace with False
        (fr"(%%\n#stack:\n)([^`\n]*)\n",
         r"\1False\n"),
        
        # Clean up the backtick marker
        (r"`",
         r"")
    ]

@instruction
def neq():
    return [*eq(),
            *boolean_not()]

@instruction
def lit_assign(varname, value):
    # Assign a literal value to a variable
    return [(r"(%%[^%]*)(#" + varname + r": )[^\n]*",  # Find the variable
            r"\1\2" + value)]                          # Replace its value
    # Groups:
    # 1: Everything from %% to the variable name
    # 2: The variable declaration (#varname: )
    # Result: Updates the variable's value

@instruction
def assign(src_var, dst_var):
    # Copy value from source variable to destination variable
    return [(r"(%%[^%]*#" + src_var + r": )([^\n]*)(.*#" + dst_var + r": )[^\n]*",
            r"\1\2\3\2")]
    # Groups:
    # 1: Everything from %% through source variable declaration
    # 2: Source variable's value
    # 3: Everything between source and destination, including destination declaration
    # Result: Copies source value to destination while preserving both variables

@instruction
def cond(tag):
    # Handle conditional execution based on stack value
    return [(r"%(%\n#stack:\nTrue)",    # If True on stack
             r"%\1`"),                     # Mark section for processing
            (r"%(\n#stack:\nFalse)",    # If False on stack
             tag+r"\1`"),                  # Mark section for processing
            (r"\n(True|False)`\n",           # Clean up True/False and marker
             "\n")]
    # Uses backtick to mark processed conditions
    # Removes True/False from stack after condition is checked

@instruction
def reactivate(tag):
    return [(r"%"+tag+r"\n([^%]*)",
             r"%%\n\1")]


@instruction
def pause(tag):
    return [(r"%%\n([^%]*)",
             r"%"+tag+r"\n\1")]

@instruction
def fork_bool(variable):
    return [(r"%%\n([^%]*)",
             r"%%\n\1#"+variable+r": True\n%%\n\1#"+variable+r": False\n")
            ]

@instruction
def fork_inactive(tag):
    return [(r"%%\n([^%]*)",
             r"%%\n\1" + "%"+tag+r"\n\1")
            ]

@instruction
def fork_with_new_var(tag, vars):
    # Creates a copy of the active thread and adds a new variable to the inactive copy
    # The original thread stays active, the copy becomes inactive and tagged
    # tag: tag to mark the inactive thread
    # var: name of the new variable to create
    # name: value to assign to the new variable
    return [(r"%%\n([^%]*)",              # Match active thread
            r"%%\n\1%" + tag + r"\n\1" + "\n".join("#"+var + r": " + val for var, val in vars.items())  + r"\n")]
    # Groups:
    # 1: ([^%]*) - Captures the entire thread content
    # Result: Creates two threads:
    #   1. Active thread (%%): Original content unchanged
    #   2. Inactive thread (%tag): Original content plus new variable

@instruction
def fork_list_pop(src_list_var, dst_var, tag):
    return [*list_pop(src_list_var, None),
            *fork_inactive('zztmp'),
            *pause('zz1tmp'),
            *reactivate('zztmp'),
            *assign_pop(dst_var),
            *delete_var(src_list_var),
            *pause(tag),
            *reactivate('zz1tmp'),
            *pop()]

@instruction
def fix_double_list():
    return [(";;", ";")]*10 + [(": ;", ": ")]

@instruction
def destroy_active_threads():
    return [(r"(%%\n[^%]*)",
             r"")
            ]

@instruction
def variable_uniq(variable, maxn=10):
    uniq = [
        # Match duplicates anywhere in the list
        (r"(%%[^%]*#"+variable+r": [^\n]*)([^;\n]*;)\2+([^%\n]*)",
         r"\1\2\3")
    ]
    return uniq * maxn

def expand_castling():
    """Convert FEN castling rights (KQkq) to individual boolean variables."""
    patterns = []
    
    # Generate all possible combinations
    pieces = ['K', 'Q', 'k', 'q']
    for i in range(2**4):  # 16 possibilities
        # Create the FEN castling string
        fen_str = ''
        bools = []
        for j, piece in enumerate(pieces):
            if i & (1 << j):
                fen_str += piece
                if piece == 'K':
                    bools.append("white_king: True")
                elif piece == 'Q':
                    bools.append("white_queen: True")
                elif piece == 'k':
                    bools.append("black_king: True")
                elif piece == 'q':
                    bools.append("black_queen: True")
            else:
                if piece == 'K':
                    bools.append("white_king: False")
                elif piece == 'Q':
                    bools.append("white_queen: False")
                elif piece == 'k':
                    bools.append("black_king: False")
                elif piece == 'q':
                    bools.append("black_queen: False")
        
        if not fen_str:
            fen_str = '-'
            
        patterns.append((
            f"(%%[^%]*)(#castling: {fen_str}\\n)",
            "\\1" + "\n".join([f"#castle_{b}" for b in sorted(bools)]) + "\n"
        ))

    # Remove the original castling line
    patterns.append((
        r"#castling: [KQkq-]+\n",
        r""
    ))
    
    return patterns

@instruction
def fen():
    return [("(%%\n#stack:\n[^ ]*) [^\n]*\n", r"\1\n")]

@instruction
def expand_chess():
    return [
        # 1) Move FEN from stack top to #fen:
        (r"(%%\n#stack:\n)([^\n]+)\n([^%]*)",
         r"\1\3#fen: \2\n"),

        # 2) Extract the turn from FEN. The FEN format is typically:
        #    [piece_placement] [turn] [castling] [en_passant] [halfmove] [fullmove]
        # We only need turn (w or b). This assumes at least two fields in the FEN.
        # After this step, we have #fen: [piece_placement] on one line
        # and #turn: w or #turn: b on another line.

        (r"(#fen:\s+)([rnbqkpRNBQKP1-8/]+)\s+([wb])\s+([KQkq]+|-)\s+([a-h][1-8]|-).*",
         r"\1\2\n#turn: \3\n#castling: \4\n#ep: \5"),

        # 3) Split the piece_placement (in #fen:) into ranks #rank8: ... through #rank1: ...
        # piece_placement = something like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        (r"(#fen:\s+)([^/]*)/([^/]*)/([^/]*)/([^/]*)/([^/]*)/([^/]*)/([^/]*)/([^ \n]*)",
         r"#fen:\n#rank8: \2\n#rank7: \3\n#rank6: \4\n#rank5: \5\n#rank4: \6\n#rank3: \7\n#rank2: \8\n#rank1: \9"),

        # 4) Expand digits into spaces for all ranks:
        # Replace '8' with 8 spaces
        (r"(#rank\d+:.*)8", r"\1        "),
        # Replace '7' with 7 spaces
        (r"(#rank\d+:.*)7", r"\1       "),
        # Replace '6' with 6 spaces
        (r"(#rank\d+:.*)6", r"\1      "),
        # Replace '5' with 5 spaces
        (r"(#rank\d+:.*)5", r"\1     "),
        # Replace '4' with 4 spaces
        (r"(#rank\d+:.*)4", r"\1    "),
        # Replace '3' with 3 spaces
        (r"(#rank\d+:.*)3", r"\1   "),
        # Replace '2' with 2 spaces
        (r"(#rank\d+:.*)2", r"\1  "),
        # Replace '1' with 1 space
        (r"(#rank\d+:.*)1", r"\1 "),
        (r"(#rank\d+:.*)3", r"\1   "),
        # Replace '2' with 2 spaces
        (r"(#rank\d+:.*)2", r"\1  "),
        # Replace '1' with 1 space
        (r"(#rank\d+:.*)1", r"\1 "),
        (r"(#rank\d+:.*)3", r"\1   "),
        # Replace '2' with 2 spaces
        (r"(#rank\d+:.*)2", r"\1  "),
        # Replace '1' with 1 space
        (r"(#rank\d+:.*)1", r"\1 "),
        # Replace '2' with 2 spaces
        (r"(#rank\d+:.*)2", r"\1  "),
        # Replace '1' with 1 space
        (r"(#rank\d+:.*)1", r"\1 "),
        (r"(#rank\d+:.*)1", r"\1 "),

        # Apply these digit-to-space replacements repeatedly until no more digits remain.
        # (The rewriting framework typically re-applies rules until stable.)

        # 5) Each rank now has exactly 8 chars representing pieces or spaces.
        # We break each #rankX: line into #aX:, #bX:, ..., #hX:
        # Capturing each character:
        (r"#rank(\d+): (.{1})(.{1})(.{1})(.{1})(.{1})(.{1})(.{1})(.{1})",
         r"#a\1: \2\n#b\1: \3\n#c\1: \4\n#d\1: \5\n#e\1: \6\n#f\1: \7\n#g\1: \8\n#h\1: \9"),
        
        *expand_castling(),

        # 6) Remove the #fen: line as it is no longer needed:
        (r"#fen:[^\n]*\n", r"")
    ]

import re

def zzassign_stack_to(variables, var, max_repeats=10):
    """
    Repeatedly pops items from stack and appends them with semicolons to variable.
    Args:
        variables: Variables instance to call instructions on
        var: Variable name to append to 
        max_repeats: Maximum number of items to process
    """
    # Create the variable if needed with empty string
    variables[var] = ""
    
    # Process up to max_repeats items
    for _ in range(max_repeats):
        # Check if stack is empty
        if variables.is_stack_empty().ite():
            pass
        else:
            variables[var] += variables.peek()
            variables[var] += ';'
        variables.merge()
    return variables

@instruction
def assign_stack_to(var, max_repeats=10):
    return [
        *push(""),
        *assign_pop(var)
        ] + [
            (f"(%%\n#stack:\n)([^%#\n]*)\n([^%]*#{var}: )([^\n]*)",
             r"\1\3\2;\4")
        ]*max_repeats

@instruction
def contract_spaces():
    # Replace runs of spaces with a single digit, starting from the largest run (8) down to 1.
    # Apply repeatedly until no more spaces remain.
    x = [
        (r"(#rank._fen: [^\n]*)(        )", r"\g<1>8"),
        (r"(#rank._fen: [^\n]*)(       )", r"\g<1>7"),
        (r"(#rank._fen: [^\n]*)(      )", r"\g<1>6"),
        (r"(#rank._fen: [^\n]*)(     )", r"\g<1>5"),
        (r"(#rank._fen: [^\n]*)(    )", r"\g<1>4"),
    ] + [
        (r"(#rank._fen: [^\n]*)(   )", r"\g<1>3")
    ] * 2 + [
        (r"(#rank._fen: [^\n]*)(  )", r"\g<1>2"),
    ] * 3 + [
        (r"(#rank._fen: [^\n]*)( )", r"\g<1>1")
    ] * 5
    return x

@instruction
def contract_chess():
    return [
        # 1) Combine each rank's squares into a single line:
        # For rank 1 as an example:
        # #a1: X\n#b1: Y\n...#h1: Z  =>  #rank1_fen: XYZ....H
        #
        # Do this for all ranks (1 through 8):

        # Remove white kingside castling if king or rook not in place
        (r"(%%[^%]*)(#e1: [^K\n].*\n|#h1: [^R\n].*\n)([^%]*#castle_white_king: )True",
         r"\1\2\3False"),
        
        # Remove white queenside castling if king or rook not in place
        (r"(%%[^%]*)(#e1: [^K\n].*\n|#a1: [^R\n].*\n)([^%]*#castle_white_queen: )True",
         r"\1\2\3False"),
        
        # Remove black kingside castling if king or rook not in place
        (r"(%%[^%]*)(#e8: [^k\n].*\n|#h8: [^r\n].*\n)([^%]*#castle_black_king: )True",
         r"\1\2\3False"),
        
        # Remove black queenside castling if king or rook not in place
        (r"(%%[^%]*)(#e8: [^k\n].*\n|#a8: [^r\n].*\n)([^%]*#castle_black_queen: )True",
         r"\1\2\3False"),
        
        
        (r"(%%[^%]*)#a1: ([^\n])\n#b1: ([^\n])\n#c1: ([^\n])\n#d1: ([^\n])\n#e1: ([^\n])\n#f1: ([^\n])\n#g1: ([^\n])\n#h1: ([^\n])",
         r"\1#rank1_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a2: ([^\n])\n#b2: ([^\n])\n#c2: ([^\n])\n#d2: ([^\n])\n#e2: ([^\n])\n#f2: ([^\n])\n#g2: ([^\n])\n#h2: ([^\n])",
         r"\1#rank2_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a3: ([^\n])\n#b3: ([^\n])\n#c3: ([^\n])\n#d3: ([^\n])\n#e3: ([^\n])\n#f3: ([^\n])\n#g3: ([^\n])\n#h3: ([^\n])",
         r"\1#rank3_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a4: ([^\n])\n#b4: ([^\n])\n#c4: ([^\n])\n#d4: ([^\n])\n#e4: ([^\n])\n#f4: ([^\n])\n#g4: ([^\n])\n#h4: ([^\n])",
         r"\1#rank4_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a5: ([^\n])\n#b5: ([^\n])\n#c5: ([^\n])\n#d5: ([^\n])\n#e5: ([^\n])\n#f5: ([^\n])\n#g5: ([^\n])\n#h5: ([^\n])",
         r"\1#rank5_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a6: ([^\n])\n#b6: ([^\n])\n#c6: ([^\n])\n#d6: ([^\n])\n#e6: ([^\n])\n#f6: ([^\n])\n#g6: ([^\n])\n#h6: ([^\n])",
         r"\1#rank6_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a7: ([^\n])\n#b7: ([^\n])\n#c7: ([^\n])\n#d7: ([^\n])\n#e7: ([^\n])\n#f7: ([^\n])\n#g7: ([^\n])\n#h7: ([^\n])",
         r"\1#rank7_fen: \2\3\4\5\6\7\8\9"),
        (r"(%%[^%]*)#a8: ([^\n])\n#b8: ([^\n])\n#c8: ([^\n])\n#d8: ([^\n])\n#e8: ([^\n])\n#f8: ([^\n])\n#g8: ([^\n])\n#h8: ([^\n])",
         r"\1#rank8_fen: \2\3\4\5\6\7\8\9"),


        
        # 2) Contract castling rights into FEN format
        # Create empty temp castling variable
        (r"(%%[^%]*)#castle_black_king: ([^\n]*)\n#castle_black_queen: ([^\n]*)\n#castle_white_king: ([^\n]*)\n#castle_white_queen: ([^\n]*)\n",
         r"\1#castle_black_king: \2\n#castle_black_queen: \3\n#castle_white_king: \4\n#castle_white_queen: \5\n#castling_temp: \n"),


        (r"(#castle_white_king: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1K"),
        (r"(#castle_white_queen: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1Q"),
        (r"(#castle_black_king: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1k"),
        (r"(#castle_black_queen: True\n[^%]*#castling_temp: [^\n]*)", 
         r"\1q"),
        
        # If no castling rights, use "-"
        (r"(#castling_temp: )\n",
         r"\1-\n"),

        # 4) Convert runs of spaces in fen_line to digits.
        # We'll rely on a separate function to produce these rules, which we will then
        # apply repeatedly until no spaces remain.
    ] + contract_spaces() + [
        
        # 3) Combine all ranks into a single fen_line (note fen order: rank8/rank7/.../rank1):
        (r"#rank8_fen: ([^\n]+)\n#rank7_fen: ([^\n]+)\n#rank6_fen: ([^\n]+)\n#rank5_fen: ([^\n]+)\n#rank4_fen: ([^\n]+)\n#rank3_fen: ([^\n]+)\n#rank2_fen: ([^\n]+)\n#rank1_fen: ([^\n]+)",
         r"#fen_line: \1/\2/\3/\4/\5/\6/\7/\8"),
         
        # 5) Add turn and castling info to fen_line:
        (r"#fen_line: ([^\n]+)\n#turn: ([wb])\n#castle_[^:]+:.*\n#castle_[^:]+:.*\n#castle_[^:]+:.*\n#castle_[^:]+:.*\n#castling_temp: ([^\n]+)\n#ep: ([^\n]+)",
         r"#fen_line: \1 \2 \3 \4"),

        # 6) Clean up intermediate variables
        (r"(%%[^%]*)(#[a-h]\d:[^\n]*\n)*", r"\1"),
        (r"(%%[^%]*)(#rank\d+_fen:[^\n]*\n)", r"\1"),
        (r"(%%[^%]*)(#castle_[^:]+:[^\n]*\n)", r"\1"),
        (r"(%%[^%]*)(#castling_temp:[^\n]*\n)", r"\1"),

        # 7) Move fen_line back onto the stack:
        (r"(%%\n#stack:\n)([^%]*)#fen_line: ([^\n]+)\n",
         r"\1\3\n\2"),

        # 8) Remove any remaining intermediate variables
        (r"(%%[^%]*)(#fen_line:[^\n]*\n)", r"\1"),
        (r"(%%[^%]*)(#turn:[^\n]*\n)", r"\1"),
        (r"(%%[^%]*)(#ep:[^\n]*\n)", r"\1")    ]

@instruction
def binary_add():
    patterns = []

    patterns.append((
        r"(%%\n#stack:\n)",
        r"\1bit:\n",
    ))
    
    for bit in range(10):
        patterns.append((
            rf"(%%\n#stack:\nbit:)AA",
            rf"\1A"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:A*)\nint([01]{{{9-bit}}})1([01]{{{bit}}})",
            rf"\1A\nint\g<2>0\g<3>"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:A*)(\nint.*\nint[01]{{{9-bit}}}1[01]{{{bit}}})",
            rf"\1A\2"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:(AA|))A\nint([01]{{{9-bit}}})0([01]{{{bit}}})",
            rf"\1\nint\g<3>1\g<4>"
        ))
    patterns.extend(pop())
    patterns.extend(swap())
    patterns.extend(pop())
    
    return patterns

@instruction
def binary_subtract():
    patterns = []

    patterns.append((
        r"(%%\n#stack:\n)",
        r"\1bit:A\n",
    ))
    
    for bit in range(10):
        patterns.append((
            rf"(%%\n#stack:\nbit:)AA",
            rf"\1A"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:A*)\nint([01]{{{9-bit}}})1([01]{{{bit}}})",
            rf"\1A\nint\g<2>0\g<3>"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:A*)(\nint.*\nint[01]{{{9-bit}}}0[01]{{{bit}}})",
            rf"\1A\2"
        ))
        patterns.append((
            rf"(%%\n#stack:\nbit:(AA|))A\nint([01]{{{9-bit}}})0([01]{{{bit}}})",
            rf"\1\nint\g<3>1\g<4>"
        ))
    patterns.extend(pop())
    patterns.extend(swap())
    patterns.extend(pop())
    patterns.append((
        rf"(%%\n#stack:\n)int1[01]*",
        rf"\1int0000000000"
    ))
    
    return patterns


@instruction
def to_unary():
    patterns = []
    
    # Process each bit from left (bit=9) down to right (bit=0)
    for bit in reversed(range(10)):
        place_val = 2 ** bit
        patterns.append((
            rf"(%%\n#stack:\n)int([01]{{{9-bit}}})1([01]{{{bit}}})",
            rf"\1int\g<2>0\g<3>{'A'*place_val}"
        ))
    
    # Finally, remove all 'int0*' if only zeros remain in the binary part
    # so that the result is purely unary 'A's (or nothing if it was zero).
    patterns.append((
        r"(%%\n#stack:\n)(int0*)",
        r"\1"
    ))
    
    return patterns

@instruction
def from_unary():
    patterns = []
    
    # 1) Insert a temporary "int" prefix with no bits decided yet.
    #    We'll rebuild bits into that. We match ANY unary As
    #    after "#stack:\n" and turn it into "int + those As".
    #
    #    So: "%%\n#stack:\nAAAA" -> "%%\n#stack:\nintAAAA"
    #
    patterns.append((
        r"(%%\n#stack:\n)(A*)",
        r"\1int\g<2>"
    ))
    
    # 2) For each bit from 9 down to 0, test whether we have >= 2^bit A's left.
    for bit in reversed(range(10)):
        place_val = 2**bit
        
        # (a) If we have at least 'place_val' A's, set that bit to '1'.
        patterns.append((
            rf"(%%\n#stack:\nint[01]*)(A{{{place_val}}})(A*)",
            rf"\g<1>1\g<3>"
        ))
        
        # (b) Otherwise, set that bit to '0'.
        patterns.append((
            rf"(%%\n#stack:\n)int([01]{{{9-bit}}})([^01]A*)",
            rf"\1int\g<2>0\g<3>"
        ))
    
    return patterns

@instruction
def add_unary():
    # Add top two unary numbers by concatenating their A's
    return [(r"(%%\n#stack:\n)(A*)\n(A*)\n",  # Match top two unary numbers
            r"\1\2\3\n")]                         # Concatenate them together
    # Groups:
    # 1: (%%\n#stack:\n) - Matches from %% through #stack:\n
    # 2: (A*) - Captures first unary number (sequence of A's)
    # 3: (A*) - Captures second unary number (sequence of A's)
    # Result: Combines both sequences of A's into single sum




@instruction
def sub_unary():
    """
    Subtract the top unary number (B) from the next unary number (A) on the stack.
    Both A and B are represented as sequences of 'A's.
    The result (A - B) is pushed back onto the stack.
    If B is greater than A, the result is zero (no 'A's).
    """
    return [
        # Pattern 1: A >= B
        (
            r"(%%\n#stack:\n)"    # Group 1: Thread and #stack header
            r"(A*)\n"                # Group 2: B (top of stack)
            r"\2(A*)\n",             # Group 3: A starts with B's A's, Group 4: Remaining A's after subtraction
            r"\1`sub\3\n"            # Replacement: Mark with `sub and push remaining A's
        ),
        # Pattern 2: A < B
        (
            r"(%%\n#stack:\n)"    # Group 1: Thread and #stack header
            r"(A*)\n"                # Group 2: B (top of stack)
            r"(A*)\n",               # Group 3: A
            r"\1`zero\n"             # Replacement: Mark with `zero
        ),
        # Pattern 3: Finalize subtraction by removing `sub
        (
            r"`sub(A*)\n",           # Match the `sub marker followed by remaining A's
            r"\1\n"                  # Replace with the remaining A's only
        ),
        # Pattern 4: Finalize zero by removing `zero
        (
            r"`zero\n",              # Match the `zero` marker
            r"\n"                     # Replace with nothing (zero result)
        ),
    ]


@instruction
def mod2_unary():
    return [(r"(%%\n#stack:\n)(A*)\2\n", 
             r"\1`True\n"),
            (r"(%%\n#stack:\n)[^`\n][^\n]*\n", 
             r"\1`False\n"),
            (r"(%%\n#stack:\n)\n\n", 
             r"\1`False\n"),
            ("`", "")
            
            ]
    
@instruction
def string_cat():
    # Add top two unary numbers by concatenating their A's
    return [(r"(%%\n#stack:\n)([^\n]*)\n([^\n]*)\n",  # Match top two unary numbers
            r"\1\2\3\n")]                         # Concatenate them together
    # Groups:
    # 1: (%%\n#stack:\n) - Matches from %% through #stack:\n
    # 2: ([^\n]*) - Captures first string
    # 3: ([^\n]*) - Captures second string
    # Result: Combines both sequences into single string
    
@instruction
def boolean_not():
    return [
        # Convert True to False (marked with backtick)
        (r"(%%\n#stack:\n)True\n",
         r"\1`False\n"),
         
        # Convert False to True (marked with backtick)
        (r"(%%\n#stack:\n)False\n",
         r"\1`True\n"),
         
        # Remove the backtick marker
        (r"`",
         r"")
    ]

@instruction
def boolean_and():
    return [
        # True AND True = True (marked with backtick)
        (r"(%%\n#stack:\n)True\nTrue\n",
         r"\1`True\n"),
         
        # Any other combination = False (if not already marked)
        (r"(%%\n#stack:\n)([^`][^\n]*)\n([^\n]*)\n",
         r"\1False\n"),
         
        # Remove the backtick marker
        (r"`",
         r"")
    ]

@instruction
def boolean_or():
    return [
        # False OR False = False (marked with backtick)
        (r"(%%\n#stack:\n)False\nFalse\n",
         r"\1`False\n"),
         
        # Any other combination = True (if not already marked)
        (r"(%%\n#stack:\n)([^`][^\n]*)\n([^\n]*)\n",
         r"\1True\n"),
         
        # Remove the backtick marker
        (r"`",
         r"")
    ]

@instruction
def greater_than():
    return [
        # If first has more A's than second with some remainder, it's greater
        # Match: first sequence followed by second sequence plus at least one more A
        (r"(%%\n#stack:\n)(A*)(A+)\n\2\n",  # Pattern matches when first > second
         r"\1`True\n"),
         
        # If not already marked True, then first isn't greater
        # Use * instead of + to allow empty strings
        (r"(%%\n#stack:\n)([^`\n]*)\n([^\n]*)\n",  # Any two values including empty
         r"\1False\n"),
        
        # Remove the backtick marker from True results
        (r"`",
         r"")
    ]

@instruction
def less_than():
    return [
        *swap(),
        *greater_than(),
    ]

@instruction
def less_equal_than():
    return [
        *greater_than(),
        *boolean_not()
    ]

@instruction
def greater_equal_than():
    return [
        *less_than(),
        *boolean_not()
    ]

@instruction
def intxy_to_location(var1, var2):
    out = lookup(var1) + lookup(var2)

    for i in range(8):
        out.append((r"(%%\n#stack:\n)"+i2s(i),
                    r"\g<1>"+str(i+1)))
    out += swap()

    for i in range(8):
        out.append((r"(%%\n#stack:\n)"+i2s(i),
                    r"\g<1>"+chr(0x61+i)))

    out += string_cat()

    return out

@instruction
def square_to_xy():
    # First convert the file (a-h) to number (0-7)
    file_patterns = []
    for i, file in enumerate('abcdefgh'):
        file_patterns.append((
            r"(%%\n#stack:\n)" + file + r"([1-8])\n",
            r"\1" + i2s(i) + r"\n\2\n"
        ))

    # Then convert the rank (1-8) to number (0-7)
    rank_patterns = []
    for i in range(1, 9):
        rank_patterns.append((
            r"(%%\n#stack:\n)([^\n]*)\n" + str(i) + r"\n",
            r"\1\2\n" + i2s(i-1) + r"\n"
        ))

    return file_patterns + rank_patterns


@instruction
def join_pop(sub):
    return [(r"(%%\n#stack:\n)(.*\n)([^%]*)%"+sub+r"\n#stack:\n(.*\n)[^%]*",
             r"\1\4\2\3")]

@instruction
def delete_var(var):
    return [
        # Match and remove the entire variable line
        (r"(%%[^%]*)(#"+var+r": [^\n]*\n)",
         r"\1")
    ]

@instruction
def list_pop(src_list_var, dst_var):
    """
    Pop first item from a semicolon-delimited list variable and assign to destination variable.
    
    1. Takes everything up to first semicolon from source list variable
    2. Puts that value on top of stack 
    3. Updates source list variable to remove the popped item
    4. Assigns top of stack to destination variable using assign_pop
    
    Args:
        src_list_var: Source list variable name to pop from
        dst_var: Destination variable name to assign popped value to
    """
    # First get everything before first semicolon onto stack,
    # and update source variable to remove it
    patterns = [
        # Handle case with items after semicolon:
        # Take first item to stack, leave rest in variable

        (r"(%%[^%]*#stack:\n)([^%]*#" + src_list_var + r": )([^\n;]*);([^;\n]*)",
         r"\1\3\n\2\4"),
    ]

    if dst_var is not None:
        # Then use assign_pop to move stack top to destination
        patterns.extend(assign_pop(dst_var))
    
    return patterns

@instruction
def make_pretty(has_move):
    # Build the capture pattern
    capture_pattern = ''
    files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
    
    for rank in ranks:
        for file in files:
            capture_pattern += f"#{file}{rank}:\\s*([kqrbnpKQRBNP ])\\s*"

    # The board template with capture group references
    board_template = """  ╔═════════════════╗
8 ║ \\1 \\2 \\3 \\4 \\5 \\6 \\7 \\8 ║
7 ║ \\9 \\10 \\11 \\12 \\13 \\14 \\15 \\16 ║
6 ║ \\17 \\18 \\19 \\20 \\21 \\22 \\23 \\24 ║
5 ║ \\25 \\26 \\27 \\28 \\29 \\30 \\31 \\32 ║
4 ║ \\33 \\34 \\35 \\36 \\37 \\38 \\39 \\40 ║
3 ║ \\41 \\42 \\43 \\44 \\45 \\46 \\47 \\48 ║
2 ║ \\49 \\50 \\51 \\52 \\53 \\54 \\55 \\56 ║
1 ║ \\57 \\58 \\59 \\60 \\61 \\62 \\63 \\64 ║
  ╚═════════════════╝
    a b c d e f g h

~"""


    # Return list of (pattern, replacement) tuples
    return [
        (r"%%\n", r""),
        
        # First pattern: Capture all positions and create board layout
        (capture_pattern, board_template),

        (r"#castle_black_king: ([^\n]*)\n#castle_black_queen: ([^\n]*)\n#castle_white_king: ([^\n]*)\n#castle_white_queen: ([^\n]*)\n",
         r"#castle_black_king: \1\n#castle_black_queen: \2\n#castle_white_king: \3\n#castle_white_queen: \4\n#castling_temp: \n"),


        (r"(.*#castle_white_king: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1K"),
        (r"(.*#castle_white_queen: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1Q"),
        (r"(.*#castle_black_king: True\n[^%]*#castling_temp: [^\n]*)",
         r"\1k"),
        (r"(.*#castle_black_queen: True\n[^%]*#castling_temp: [^\n]*)", 
         r"\1q"),
        
        # If no castling rights, use "-"
        (r"(.*#castling_temp: )\n",
         r"\1-\n"),

        
        (r"#castling_temp: ([^\n]*)\n#ep: ([^\n]*)\n",
         r"[Castling Rights: \1, En Passant: \2]\n"),
        
        (r"#[^a-h].*\n", ""),
        (r"#.[^1-8].*\n", ""),
    ] + [
        # Second pattern: Convert pieces to UTF-8 symbols
        ("║(.*)K", r"║\1♔"), ("║(.*)Q", r"║\1♕"), ("║(.*)R", r"║\1♖"), ("║(.*)B", r"║\1♗"), ("║(.*)N", r"║\1♘"), ("║(.*)P", r"║\1♙"),
        ("║(.*)k", r"║\1♚"), ("║(.*)q", r"║\1♛"), ("║(.*)r", r"║\1♜"), ("║(.*)b", r"║\1♝"), ("║(.*)n", r"║\1♞"), ("║(.*)p", r"║\1♟")
    ] * 8 + [

        
    ] + ([("~", "Move notation: [src][dest] (e.g. e2e4) or 'q' to quit\n"), (r"\]\n", r"]\nEnter Your Move: ")]  if has_move else [("~","\n")])



@instruction
def unpretty(has_move):
    # Create piece conversions
    pieces = {
        'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
        'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
    }
    
    # Create board coordinates
    files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
    
    # Build the piece pattern
    piece_chars = ''.join(pieces.values()) + ' '
    piece_pattern = f'[{piece_chars}]'
    
    # Generate board pattern programmatically
    board_lines = [
        "  ╔═════════════════╗"
    ]
    
    for rank in ranks:
        captures = ' '.join(f'({piece_pattern})' for _ in files)
        board_lines.append(f"{rank} ║ {captures} ║")
    
    board_lines.extend([
        "  ╚═════════════════╝",
        "    a b c d e f g h",
        "",
        ".*",
        r"\[Castling Rights: (.*), En Passant: (.*)\]",
    ])
    if has_move:
        board_lines.append(
            r"Enter Your Move: ([a-h][1-8][a-h][1-8]|q)(%|[^%])*"   # Move input - capture group for the move
        )
    else:
        board_lines.append(
            "[^%]*"
            )

    
    board_pattern = '\n'.join(board_lines)
    
    # Generate replacement template
    replacement_lines = ["%%\n#stack:"]
    pos = 1
    for rank in ranks:
        for file in files:
            replacement_lines.append(f"#{file}{rank}: \\{pos}")
            pos += 1
    
    # Add src and dst variables for the move (using capture group \65 for the move)
    replacement_lines.extend([
        "#turn: w",
        "#castling: \\65",
        "#ep: \\66",
    ])
    if has_move:
        replacement_lines.extend([
        "#move: \\67",
        "#src: \\67",
        "#dst: \\67\n",
            ])
    else:
        replacement_lines.append("")
        
            
    replacement = '\n'.join(replacement_lines)
    
    # Build patterns list
    patterns = [(board_pattern, replacement),             *expand_castling()]

    if has_move:
        # Add patterns to split move into src and dst
        patterns.extend([
            
            # Extract first two characters for src
            (r"#src: ([a-h])([1-8])[a-h][1-8]", r"#src: \1\2"),
            # Extract last two characters for dst
            (r"#dst: [a-h][1-8]([a-h])([1-8])", r"#dst: \1\2"),
        ])
    patterns.append((r"[ \n]*%", "%"))
    
    # Add piece conversion patterns
    patterns.extend((unicode_piece, letter) for letter, unicode_piece in pieces.items())
    
    return patterns

@instruction
def piece_value():
    """
    Computes material value of a chess position in FEN notation.
    Returns value as (white - black + 100) to keep positive
    """
    # Remove all numbers (apply multiple times)
    patterns = [(r"(%%\n#stack:\n[^ ]*) [^\n]*", r"\1")]
    patterns += [(r"(%%\n#stack:\n[^\n]*)[ /1-8]([^\n]*\n)", r"\1\2")] * 32

    # Duplicate the stack for white and black calculations
    patterns.extend(dup())

    # For white value: Remove all lowercase (apply multiple times)
    patterns.extend([
        (r"(%%\n#stack:\n[^\n]*)([a-z])([^\n]*\n)", r"\1\3")
    ] * 32)

    # Convert white pieces to unary values (apply each multiple times)
    for piece, value in [
        ("K", 2*"AAAAAAAAAA"), # King = 10
        ("Q", 2*"AAAAAAAAA"),  # Queen = 9
        ("R", 2*"AAAAA"),      # Rook = 5
        ("B", 2*"AAA"),        # Bishop = 3
        ("N", 2*"AAA"),        # Knight = 3
        ("P", 2*"A"),          # Pawn = 1
    ]:
        patterns.extend([
            (r"(%%\n#stack:\n[^\n]*)"+piece+r"([^\n]*\n)", r"\1"+value+r"\2")
        ] * 16)

    # Swap to process second element
    patterns.extend(swap())

    # For black value: Remove all uppercase (apply multiple times)
    patterns.extend([
        (r"(%%\n#stack:\n[^\n]*)([A-Z])([^\n]*\n)", r"\1\3")
    ] * 32)

    # Convert black pieces to unary values (apply each multiple times)
    for piece, value in [
        ("k", 2*"AAAAAAAAAA"), # King = 10
        ("q", 2*"AAAAAAAAA"),  # Queen = 9
        ("r", 2*"AAAAA"),      # Rook = 5
        ("b", 2*"AAA"),        # Bishop = 3
        ("n", 2*"AAA"),        # Knight = 3
        ("p", 2*"A"),          # Pawn = 1
    ]:
        patterns.extend([
            (r"(%%\n#stack:\n[^\n]*)"+piece+r"([^\n]*\n)", r"\1"+value+r"\2")
        ] * 16)

    # Push 200 in unary (200 A's)
    patterns.extend(push("A" * 200))

    # Add white pieces value
    patterns.extend(swap())
    patterns.extend(sub_unary())

    # Subtract black pieces value
    patterns.extend(add_unary())

    return patterns

@instruction
def check_king_alive():
    return [(r"%%([^%]*#next_boards: [^\n]*;([^k/;]*/){7}[^k/;\n]*[ ;][^\n]*\n)",
             r"%%`\1#alive: False\n"),
            (r"%%([^%]*#next_boards: [^\n]*;([^K/;]*/){7}[^K/;\n]*[ ;][^\n]*\n)",
             r"%%`\1#alive: False\n"),
            (r"%%([^`][^%]*)",
             r"%%\1#alive: True\n"),
            (r"`", "")
            ]

@instruction
def promote_to_queen():
    return [(fr"(%%[^%]*#{r}1: )p", r"\1q") for r in "abcdefgh"] + [(fr"(%%[^%]*#{r}8: )P", r"\1Q") for r in "abcdefgh"]

@instruction
def keep_only_first_thread():
    return [("(%%[^%]*)([^%]|%)*",
             r"\1")]

@instruction
def keep_only_max_thread():
    return [(r"(%%\n#stack:\n(A+)\n[^%]*)(%%\n#stack:\n\2A*[^%]*)",
             r"\1"),
            (r"(%%[^%]*)(%%[^%]*)", r"\2\1"),
            ]*50

@instruction
def keep_only_last_thread():
    return [("([^%]|%)*(%%[^%]*)",
             r"\2")]

@instruction
def keep_only_min_thread():
    return [(r"(%%\n#stack:\n(A+)\n[^%]*)(%%\n#stack:\n\2A*[^%]*)",
             r"\1"),
            (r"(%%[^%]*)(%%[^%]*)", r"\2\1"),
            ]*50


@instruction
def illegal_move():
    return [("^[^%<]*$",
             "*Illegal Move*\nYou Lose.\nGame over.\n")]

@instruction
def test_checkmate():
    return [("^[^*%<]*$",
             "*Checkmate*\nYou win!\nGame over.\n")]

@instruction
def do_piece_assign(piece_chr, piece, x, y, pos):
    return [(f"%%([^%]*#{pos}: {piece_chr}[^%]*)#{piece}x_lst: ([^\n]*)\n#{piece}y_lst: ([^\n]*)\n#{piece}pos_lst: ([^\n]*)\n",
             fr"%%\1#{piece}x_lst: {x};\2\n#{piece}y_lst: {y};\3\n#{piece}pos_lst: {pos};\4\n")]

def find_all_pieces(variables, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    PIECES = ['king', 'queen', 'rook', 'bishop', 'knight', 'pawn']
    for piece in PIECES:
        variables[piece+'x_lst'] = ''
        variables[piece+'y_lst'] = ''
        variables[piece+'pos_lst'] = ''

    for ii, i in enumerate('abcdefgh'):
        for j in range(1, 9):
            for piece_char, piece in zip('kqrbnp', PIECES):
                variables.do_piece_assign(color(piece_char), piece, i2s(ii), i2s(j-1), str(i)+str(j))

def find_pieces(variables, color, piece, piece_chr):
    variables[piece+'x_lst'] = ''
    variables[piece+'y_lst'] = ''
    variables[piece+'pos_lst'] = ''

    for ii, i in enumerate('abcdefgh'):
        for j in range(1, 9):
            variables.do_piece_assign(color(piece_chr), piece, i2s(ii), i2s(j-1), str(i)+str(j))
                

@instruction
def is_same_kind():
    out = []
    for piece in 'kqrbnp ':
        out.append((fr"(%%\n#stack:\n){piece.lower()}\n{piece.upper()}\n",
                    r"\1`True\n"))
    
    out.extend([
        # Any other combination = False (if not already marked)
        (r"(%%\n#stack:\n)([^`][^\n]*)\n([^\n]*)\n",
         r"\1False\n"),
         
        # Remove the backtick marker
        (r"`",
         r"")
    ])
    return out
    

def i2s(num):
    return f"int{num:010b}"
