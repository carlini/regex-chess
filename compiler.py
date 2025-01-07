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

from instruction_set import *

class CallTree:
    def __init__(self, tree=[], pointer=0):
        self.tree = tree
        self.active_path = self.tree
        self.pointer = 0
        self.pointer_hist = []
        self.active_path_hist = []

    def append(self, node):
        if self.pointer < len(self.active_path):
            assert node == self.active_path[self.pointer]
        else:
            self.active_path.append(node)
        self.pointer += 1

    def branch(self, value):
        ret_val = True
        #print("Branch")
        self.active_path_hist.append(self.active_path)
        self.pointer_hist.append(self.pointer)
        if self.pointer < len(self.active_path):
            # we've created the tree structure at least once before
            assert self.active_path[self.pointer][0] == 'branch'
            if not self.traverse(self.active_path[self.pointer][2][0]):
                if self.active_path[self.pointer][2][0] is None:
                    self.active_path[self.pointer][2][0] = []
                self.active_path = self.active_path[self.pointer][2][0]
            else:
                #print("Finished along", self.active_path[self.pointer][2][0])
                if self.active_path[self.pointer][2][1] is None:
                    self.active_path[self.pointer][2][1] = []
                self.active_path = self.active_path[self.pointer][2][1]
                ret_val = False
        else:
            #print("Do append")
            self.active_path.append(('branch', value, [[], None]))
            self.active_path = self.active_path[-1][2][0]
        self.pointer = 0
        return ret_val

            
    def merge(self):
        [*self.pointer_hist, self.pointer] = self.pointer_hist
        [*self.active_path_hist, self.active_path] = self.active_path_hist
        self.pointer += 1

    def traverse(self, path):
        if path is None: return False
        for node in path:
            if isinstance(node, (list, tuple)) and node[0] == 'branch':
                children = node[2]
                if len(children) != 2:
                    print(f"Invalid branch structure: {node}")
                    return False
                left, right = children
                if left is None or right is None:
                    #print(f"Branch with incomplete children found: {node}")
                    return False
                # Recursively check both left and right subtrees
                if not self.traverse(left):
                    return False
                if not self.traverse(right):
                    return False
        return True
        
    def is_complete(self):
        """
        Check if the CallTree is fully constructed, i.e., there are no branches with None leaves.

        Returns:
            bool: True if the tree is complete, False otherwise.
        """

        return traverse(self.tree) and len(self.tree) > 0


class Tracer:
    def __init__(self, history, value, kind):
        self.history = history
        self.value = value
        self.kind = kind

    def ite(self):
        return self.history.branch(self)

    def __eq__(self, other):
        return Tracer(self.history, ("==", self, other), "bool")

    def __ne__(self, other):
        return Tracer(self.history, ("!=", self, other), "bool")

    def fen(self):
        return Tracer(self.history, ("fen", self), "str")
    
    def __add__(self, other):
        if self.kind == 'str':
            return Tracer(self.history, ("strcat", self, other), self.kind)
        else:
            if isinstance(other, int):
                if other < 0:
                    return Tracer(self.history, ("-", self, -other), self.kind)
                else:
                    return Tracer(self.history, ("+", self, other), self.kind)
            else:
                return Tracer(self.history, ("+", self, other), self.kind)
                

    def __sub__(self, other):
        return Tracer(self.history, ("-", self, other), "int")

    def __gt__(self, other):
        return Tracer(self.history, (">", self, other), "bool")

    def __lt__(self, other):
        return Tracer(self.history, ("<", self, other), "bool")

    def __ge__(self, other):
        return Tracer(self.history, (">=", self, other), "bool")

    def __le__(self, other):
        return Tracer(self.history, ("<=", self, other), "bool")

    def __and__(self, other):
        return Tracer(self.history, ("and", self, other), "bool")

    def __or__(self, other):
        return Tracer(self.history, ("or", self, other), "bool")

    def __invert__(self):
        return Tracer(self.history, ("not", self), "bool")
    
    def __mod__(self, other):
        assert other == 2
        return Tracer(self.history, ("%2", self), "bool")

    def isany(self, other):
        return Tracer(self.history, ("isany", self, other), "bool")
        
                
    
class VarTracer:
    def __init__(self):
        self.history = CallTree(tree=[])
        self.types = {}

    def __getitem__(self, key):
        if isinstance(key, Tracer):
            return Tracer(self.history, ("indirect_lookup", key), 'str')
            
        return Tracer(self.history, ("lookup", key), self.types.get(key) or 'str')

    def settype(self, key, kind):
        self.types[key] = kind

    def __setitem__(self, key, value):
        if isinstance(value, Tracer):
            kind = value.kind
        elif isinstance(value, int):
            kind = 'int'
        elif isinstance(value, str):
            kind = 'str'
        else:
            print("UNKNOWN", value)
            raise
        self.types[key] = kind
        self.history.append(("assign", key, value))
        return Tracer(self.history, None, None)

    def merge(self):
        self.history.merge()

    def cond(self, other, tag):
        self.history.append(("cond", other, tag))

    def fork_bool(self, var):
        self.history.append(("fork_bool", var))

    def __getattr__(self, key):
        if key in INSTRUCTIONS:
            def fn(*args):
                self.history.append((key, *args))
                return Tracer(self.history, ('nop',), 'str') 
            return fn
        else:
            raise
        
                
def trace(function):
    tracer = VarTracer()
    #while not tracer.history.is_complete():
    for _ in range(10):
        tracer.history.pointer = 0
        function(tracer)
    return (tracer.history.tree)



def linearize_expr(value):
    if isinstance(value, int):
        return [("push", value)]
    if isinstance(value, str):
        return [("push", value)]
    if isinstance(value, Tracer):
        value = value.value

    op = value[0]

    remap = {"==": "eq",
             "!=": "neq",
             "strcat": "string_cat",
             'and': 'boolean_and',
             'or': 'boolean_or',
             }

    remap_cmp = {
             "<": "less_than",
             ">": "greater_than",
             "<=": "less_equal_than",
             ">=": "greater_equal_than"
    }
    
    unary_ops = {"+": "add_unary",
                 "-": "sub_unary",
                 }
    
    if op in remap:
        return [*linearize_expr(value[2]),
                *linearize_expr(value[1]),
                (remap[op],)]
    elif op in remap_cmp:
        return [*linearize_expr(value[2]),
                ('to_unary',),
                *linearize_expr(value[1]),
                ('to_unary',),
                (remap_cmp[op],)]
    elif op == "not":
        return [*linearize_expr(value[1]), ("boolean_not",)]
    elif op == '+':
        return [*linearize_expr(value[1]),
                *linearize_expr(value[2]),
                ('binary_add',)
                ]
    elif op == '-':
        return [*linearize_expr(value[2]),
                *linearize_expr(value[1]),
                ('binary_subtract',)
                ]
    elif op in unary_ops:
        return [*linearize_expr(value[1]),
                ('to_unary',),
                *linearize_expr(value[2]),
                ('to_unary',),
                (unary_ops[op],),
                ('from_unary',)
                ]
    elif op == '%2':
        return [*linearize_expr(value[1]),
                ('to_unary',),
                ("mod2_unary",),
                ]
    elif op == "lookup":
        return [("lookup", value[1])]
    elif op == "indirect_lookup":
        return [("lookup", value[1].value[1]),
                ("indirect_lookup",)]
    elif op == "isany":
        return [*linearize_expr(value[1]),
                ('isany', value[2])]
    elif op == "fen":
        return [*linearize_expr(value[1]),
                ('fen',)]
    elif op == 'nop':
        return []
    else:
        raise ValueError(f"Unknown operation: {op}")


def linearize_tree(call_tree):
    """
    Given a call tree (a nested structure of tuples like ('assign', key, value),
    ('lookup', key), ('branch', [left, right]), and possibly other operations),
    produce a linear sequence of instructions as tuples.
    """
    
    tag_counter = [0]
    def next_tag():
        tag = f"UID{tag_counter[0]}"
        tag_counter[0] += 1
        return tag

    def linearize_subtree(subtree):
        instructions = []
        for node in subtree:
            if isinstance(node, tuple):
                op = node[0]

                # Handle known operations
                if op == "assign":
                    # node = ("assign", key, value)
                    _, key, value = node
                    if isinstance(value, Tracer):
                        instructions.extend(linearize_expr(value.value))
                    else:
                        instructions.append(("push", value))
                    instructions.append(('assign_pop', key))

                elif op == "lookup":
                    # node = ("lookup", key)
                    _, key = node
                    instructions.append(('lookup', key))

                elif op == "branch":
                    # node = ("branch", [left_subtree, right_subtree])
                    _, value, (left_subtree, right_subtree) = node
                    tag1 = next_tag()
                    tag2 = next_tag()
                    instructions.extend(linearize_expr(value))
                    # cond(tag1)
                    instructions.append(('cond', tag1))
                    # true branch
                    instructions.extend(linearize_subtree(left_subtree))

                    else_case = linearize_subtree(right_subtree)
                    
                    if len(else_case) > 0:
                        instructions.append(('pause', tag2))

                        instructions.append(('reactivate', tag1))

                        # false branch
                        instructions.extend(else_case)
                        # reactivate(tag2)
                        instructions.append(('reactivate', tag2))
                    else:
                        instructions.append(('reactivate', tag1))

                elif op == "reactivate":
                    # node = ("reactivate", tag)
                    _, tag = node
                    instructions.append(('reactivate', tag))
                elif op == "fork_bool":
                    _, tag = node
                    instructions.append(('fork_bool', tag))

                elif op == "cond":
                    _, node, tag = node
                    instructions.extend(linearize_expr(node))
                    instructions.append(('cond', tag))

                elif op == "fork_with_new_var":
                    _, tag, vars = node
                    instructions.append(('fork_with_new_var', tag, vars))

                elif op in ['assign_pop', "intxy_to_location", "push", "indirect_assign", "destroy_active_threads", "pause", "join_pop", "contract_chess", "expand_chess", "list_pop", "fork_inactive", "variable_uniq", "make_pretty", "unpretty", 'is_stack_empty', 'pop', 'peek', 'fork_list_pop', 'delete_var', 'check_king_alive', 'keep_only_first_thread', 'keep_only_max_thread', 'keep_only_last_thread', 'keep_only_min_thread', 'illegal_move', 'test_checkmate', 'square_to_xy', 'do_piece_assign', 'assign_stack_to', 'piece_value', "fix_double_list", 'binary_subtract', 'swap', 'is_same_kind', 'boolean_and', 'binary_add', 'sub_unary', 'promote_to_queen']:
                    _, *args = node
                    instructions.append((op, *args))
                elif op == 'nop':
                    pass
                else:
                    # Unknown node type
                    raise ValueError(f"Unknown node type: {op}")
            else:
                # If not a tuple, unexpected structure
                raise ValueError(f"Unexpected node structure: {node}")
        return instructions

    return linearize_subtree(call_tree)

def create(sequence):
    out = []
    for op,*args in sequence:
        out.append(((op, args), eval(op)(*args)))

    #out2 = []
    #for (op, re_pairs) in out:
    #    out2.append((op, [(re.compile(x), y) for x,y in re_pairs]))
        
    return out

def re_compile(fn):
    tree = trace(fn)
    linear = linearize_tree(tree)
    args = create(linear)
    
    return args
