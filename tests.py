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

import unittest
import re
from typing import Dict, List, Tuple, Union
from dataclasses import dataclass

from instruction_set import *
from compiler import *
from chess_engine import *

@dataclass
class CPUState:
    """Represents the state of the regex CPU"""
    variables: Dict[str, str]
    stack: List[str]

    def to_string(self) -> str:
        """Convert the state to the %% format string"""
        lines = ["%%", "#stack:", *self.stack]
        for var_name, value in sorted(self.variables.items()):
            lines.append(f"#{var_name}: {value}")
        lines = "\n".join(lines)
        return lines+"\n"

    @classmethod
    def from_string(cls, state_str: str) -> 'CPUState':
        """Parse a %% format string into a CPUState"""
        if not state_str.startswith("%%"):
            raise ValueError("State must start with %%")

        variables = {}
        stack = []

        lines = state_str.split('\n')[:-1]
        in_stack = False
        
        for line in lines[1:]:  # Skip %% line
            line = line.strip()
            if not line and not in_stack:
                continue
                
            if not line.startswith('#'):
                if in_stack:
                    stack.append(line)
                continue
            
            if line == "#stack:":
                in_stack = True
                continue
                
            parts = line[1:].split(':', 1)
            if len(parts) != 2:
                continue
                
            var_name, value = parts
            variables[var_name.strip()] = value.strip()
            
        return cls(variables=variables, stack=stack)

    
def execute_instruction(state: Dict[str, str], instruction: List[Tuple[str, str]]) -> Dict[str, str]:
    """Execute a single instruction on a state dictionary"""
    # Convert dict to string format
    cpu_state = CPUState(
        variables={k: v for k, v in state.items() if k != "stack"},
        stack=state.get("stack", [])
    )
    state_str = cpu_state.to_string()
    #print("Go", repr(state_str))

    # Apply regex transformations
    for pattern, replacement in instruction:
        state_str = re.sub(pattern, replacement, state_str)
        #print(repr(state_str))

    # Convert back to dictionary
    result_state = CPUState.from_string(state_str)
    return {
        **result_state.variables,
        "stack": result_state.stack
    }

class RegexCPUTest(unittest.TestCase):
    def setUp(self):
        self.initial_state = {
            "stack": [],
            "a1": "R",
            "b1": "N",
            "c1": "B",
            "d1": "Q",
            "e1": "K",
            "f1": "B",
            "g1": "N",
            "h1": "R"
        }

    def assertStateEqual(self, actual: Dict[str, str], expected: Dict[str, str], msg=None):
        """Assert that two state dictionaries are equivalent"""
        # Ensure stack is always a list
        actual_copy = dict(actual)
        expected_copy = dict(expected)
        
        if "stack" not in actual_copy:
            actual_copy["stack"] = []
        if "stack" not in expected_copy:
            expected_copy["stack"] = []
            
        self.assertEqual(actual_copy, expected_copy, msg)

    def test_push(self):
        """Test pushing a value onto the stack"""
        
        initial = {"stack": []}
        expected = {"stack": ["test_value"]}
        
        result = execute_instruction(initial, push("test_value"))
        self.assertStateEqual(result, expected)

    def test_lookup(self):
        """Test looking up a variable's value"""
        
        initial = {
            "stack": [],
            "test_var": "test_value"
        }
        expected = {
            "stack": ["test_value"],
            "test_var": "test_value"
        }


        result = execute_instruction(initial, lookup("test_var"))
        self.assertStateEqual(result, expected)

    def test_eq_true(self):
        """Test equality comparison with equal values"""
        
        initial = {
            "stack": ["same", "same"]
        }
        expected = {
            "stack": ["True"]
        }
        
        result = execute_instruction(initial, eq())
        self.assertStateEqual(result, expected)

    def test_eq_false(self):
        """Test equality comparison with different values"""
        
        initial = {
            "stack": ["value1", "value2"]
        }
        expected = {
            "stack": ["False"]
        }
        
        result = execute_instruction(initial, eq())
        self.assertStateEqual(result, expected)

    def test_state_conversion(self):
        """Test state conversion between dict and string formats"""
        state_dict = {
            "stack": ["value1", "value2"],
            "var1": "test1",
            "var2": "test2"
        }
        
        # Convert to string and back to dict
        cpu_state = CPUState(
            variables={k: v for k, v in state_dict.items() if k != "stack"},
            stack=state_dict["stack"]
        )
        state_str = cpu_state.to_string()
        result_state = CPUState.from_string(state_str)
        
        result_dict = {
            **result_state.variables,
            "stack": result_state.stack
        }
        
        self.assertEqual(state_dict, result_dict)

    def test_assign_pop(self):
        """Test assigning a value from the stack to a variable"""
        
        initial = {
            "stack": ["test_value"],
            "test_var": "old_value"
        }
        expected = {
            "stack": [],
            "test_var": "test_value"
        }
        
        result = execute_instruction(initial, assign_pop("test_var"))
        self.assertStateEqual(result, expected)

    def test_assign_pop_noexist(self):
        """Test assigning a value from the stack to a variable"""
        
        initial = {
            "stack": ["test_value"],
        }
        expected = {
            "stack": [],
            "test_var": "test_value"
        }
        
        result = execute_instruction(initial, assign_pop("test_var"))
        self.assertStateEqual(result, expected)
        
    def test_dup(self):
        """Test duplicating the top value on the stack"""
        
        initial = {
            "stack": ["test_value"]
        }
        expected = {
            "stack": ["test_value", "test_value"]
        }
        
        result = execute_instruction(initial, dup())
        self.assertStateEqual(result, expected)
    
    def test_pop(self):
        """Test removing the top value from the stack"""
        
        initial = {
            "stack": ["value_to_remove", "remaining_value"]
        }
        expected = {
            "stack": ["remaining_value"]
        }
        
        result = execute_instruction(initial, pop())
        self.assertStateEqual(result, expected)

    def test_multiple_unary_additions(self):
        """Test multiple unary addition cases with different numbers"""
        
        def run_addition_test(num1: str, num2: str, expected: str):
            """Helper to run a single addition test case"""
            state = {"stack": []}
            
            # Push first number and convert to unary
            state = execute_instruction(state, push(f"int{num1:010b}"))
            state = execute_instruction(state, to_unary())
            
            # Push second number and convert to unary
            state = execute_instruction(state, push(f"int{num2:010b}"))
            state = execute_instruction(state, to_unary())
            
            # Add and convert back
            state = execute_instruction(state, add_unary())
            final_state = execute_instruction(state, from_unary())
            
            expected_state = {"stack": [f"int{expected:010b}"]}
            self.assertStateEqual(final_state, expected_state)
    
        # Test case 1: 12 + 34 = 46
        run_addition_test(12, 34, 46)
        
        # Test case 2: 99 + 1 = 100
        run_addition_test(99, 1, 100)
        
        # Test case 3: 220 + 80 = 300
        run_addition_test(220, 80, 300)

    def test_multiple_unary_subtractions(self):
        """Test multiple unary addition cases with different numbers"""
        
        def run_subtraction_test(num1: str, num2: str, expected: str):
            """Helper to run a single addition test case"""
            state = {"stack": []}
            
            # Push first number and convert to unary
            state = execute_instruction(state, push(f"int{num1:010b}"))
            state = execute_instruction(state, to_unary())
            
            # Push second number and convert to unary
            state = execute_instruction(state, push(f"int{num2:010b}"))
            state = execute_instruction(state, to_unary())
            
            # Add and convert back
            state = execute_instruction(state, sub_unary())
            final_state = execute_instruction(state, from_unary())
            
            expected_state = {"stack": [f"int{expected:010b}"]}
            self.assertStateEqual(final_state, expected_state)
    
        run_subtraction_test(5, 4, 1)

        run_subtraction_test(5, 0, 5)

        run_subtraction_test(5, 5, 0)

        run_subtraction_test(5, 6, 0)

        run_subtraction_test(100, 6, 94)

        run_subtraction_test(0, 0, 0)

        run_subtraction_test(0, 5, 0)
        
        
    def test_to_unary_conversion(self):
        """Test converting a decimal number to unary representation"""
        
        initial = {
            "stack": ["int0000000011"]
        }
        expected = {
            "stack": ["AAA"]  # 3 in unary
        }
        
        result = execute_instruction(initial, to_unary())
        self.assertStateEqual(result, expected)

    def test_from_unary_conversion(self):
        """Test converting from unary back to decimal"""
        
        initial = {
            "stack": ["AAAAA"]  # 5 in unary
        }
        expected = {
            "stack": ["int0000000101"]
        }
        
        result = execute_instruction(initial, from_unary())
        self.assertStateEqual(result, expected)


    def test_from_unary_conversion_zero(self):
        """Test converting from unary back to decimal"""
        
        initial = {
            "stack": [""]  # 0 in unary
        }
        expected = {
            "stack": ["int0000000000"]
        }
        
        result = execute_instruction(initial, from_unary())
        self.assertStateEqual(result, expected)

    def test_to_unary_conversion_zero(self):
        """Test converting from unary back to decimal"""
        
        initial = {
            "stack": ["int0000000000"]
        }
        expected = {
            "stack": [""]
        }
        
        result = execute_instruction(initial, to_unary())
        self.assertStateEqual(result, expected)
        
    def test_add_unary(self):
        """Test adding two unary numbers"""
        
        initial = {
            "stack": ["AAA", "AA"]  # 3 and 2 in unary
        }
        expected = {
            "stack": ["AAAAA"]  # 5 in unary
        }
        
        result = execute_instruction(initial, add_unary())
        self.assertStateEqual(result, expected)

    def test_mod2_unary(self):
        """Test adding two unary numbers"""

        for i in range(10):
            initial = {
                "stack": ["A"*i]
            }
            expected = {
                "stack": [str((i%2) == 0)]
            }
            
            result = execute_instruction(initial, mod2_unary())
            self.assertStateEqual(result, expected)
            
    def run_comparison_test(self, operation, num1: str, num2: str, expected: str):
        """Helper to run a single comparison test case
        
        Args:
            operation: Function that returns the instruction list for the comparison
            num1: First number to compare (will be second on stack)
            num2: Second number to compare (will be first on stack)
            expected: Expected result ("True" or "False")
        """
        state = {"stack": [],
                 "foo": "bar"}
        
        # Push second number (will be popped first) and convert to unary
        state = execute_instruction(state, push(f"int{num2:010b}"))
        state = execute_instruction(state, to_unary())
        
        # Push first number and convert to unary
        state = execute_instruction(state, push(f"int{num1:010b}"))
        state = execute_instruction(state, to_unary())
        
        # Compare and check result
        final_state = execute_instruction(state, operation())
        
        expected_state = {"stack": [expected],
                          "foo": "bar"}
        self.assertStateEqual(final_state, expected_state)
    
    def test_greater_than(self):
        """Test comparing two unary numbers with greater than operation"""
        test_cases = [
            (5, 3, "True"),    # Basic greater than
            (3, 5, "False"),   # Basic less than
            (5, 5, "False"),   # Equal values
            (10, 1, "True"),   # Large difference
            (0, 5, "False"),   # Zero case
            (100, 99, "True"), # Large numbers, small difference
        ]
        
        for num1, num2, expected in test_cases:
            with self.subTest(f"{num1} > {num2}"):
                self.run_comparison_test(greater_than, num1, num2, expected)
    
    def test_less_than(self):
        """Test comparing two unary numbers with less than operation"""
        test_cases = [
            (3, 5, "True"),    # Basic less than
            (5, 3, "False"),   # Basic greater than
            (5, 5, "False"),   # Equal values
            (1, 10, "True"),   # Large difference
            (5, 0, "False"),   # Zero case
            (99, 100, "True"), # Large numbers, small difference
        ]
        
        for num1, num2, expected in test_cases:
            with self.subTest(f"{num1} < {num2}"):
                self.run_comparison_test(less_than, num1, num2, expected)
    
    def test_greater_equal_than(self):
        """Test comparing two unary numbers with greater than or equal operation"""
        test_cases = [
            (5, 3, "True"),    # Basic greater than
            (3, 5, "False"),   # Basic less than
            (5, 5, "True"),    # Equal values
            (10, 1, "True"),   # Large difference
            (0, 5, "False"),   # Zero case
            (5, 0, "True"),    # Compare with zero
            (100, 99, "True"), # Large numbers, small difference
            (99, 99, "True"),  # Large equal numbers
        ]
        
        for num1, num2, expected in test_cases:
            with self.subTest(f"{num1} >= {num2}"):
                self.run_comparison_test(greater_equal_than, num1, num2, expected)
    
    def test_less_equal_than(self):
        """Test comparing two unary numbers with less than or equal operation"""
        test_cases = [
            (3, 5, "True"),    # Basic less than
            (5, 3, "False"),   # Basic greater than
            (5, 5, "True"),    # Equal values
            (1, 10, "True"),   # Large difference
            (5, 0, "False"),   # Compare with zero
            (0, 0, "True"),    # Both zero
            (99, 100, "True"), # Large numbers, small difference
            (99, 99, "True"),  # Large equal numbers
        ]
        
        for num1, num2, expected in test_cases:
            with self.subTest(f"{num1} <= {num2}"):
                self.run_comparison_test(less_equal_than, num1, num2, expected)

    def test_boolean_not(self):
        """Test negating a boolean value"""
        
        initial = {
            "stack": ["True"]
        }
        expected = {
            "stack": ["False"]
        }

        result = execute_instruction(initial, boolean_not())
        self.assertStateEqual(result, expected)

    def test_indirect_lookup(self):
        """Test indirect lookup which gets a variable name from the stack and looks up its value.
        
        Example:
        If state has:
            pointer = "target"
        And stack has:
            ["pointer"]
        
        Then indirect lookup should:
            1. Pop "pointer" from stack
            2. Push the value of pointer ("target") onto stack
        """
        
        # Test basic indirect lookup
        initial_state = {
            "stack": ["pointer"],
            "pointer": "target"
        }
        expected_state = {
            "stack": ["target"],
            "pointer": "target"
        }
        result = execute_instruction(initial_state, indirect_lookup())
        self.assertStateEqual(result, expected_state)

    def test_indirect_assign(self):
        """Test indirect assign which gets both variable name and value from the stack.
        
        Example:
        If stack has:
            ["new_value", "target"]
        
        Then indirect assign should:
            1. Pop "target" (variable name) from stack
            2. Pop "new_value" (value to assign) from stack
            3. Set variable "target" to have value "new_value"
        """
        
        # Test basic indirect assign
        initial_state = {
            "stack": ["new_value", "target"],
            "target": "old_value"
        }
        expected_state = {
            "stack": [],
            "target": "new_value"
        }
        result = execute_instruction(initial_state, indirect_assign())
        self.assertStateEqual(result, expected_state)
        
        # Test creating new variable
        initial_state = {
            "stack": ["first_value", "new_var"]
        }
        expected_state = {
            "stack": [],
            "new_var": "first_value"
        }
        result = execute_instruction(initial_state, indirect_assign())
        self.assertStateEqual(result, expected_state)

    def test_intxy_to_location(self):
        """Test conversion of integer coordinates to chess square notation.
        Tests all 64 squares from a1 to h8 programmatically.
        
        Files (1-8) map to a-h
        Ranks stay as numbers 1-8
        """
        # Generate and test all squares
        for file in range(1, 9):  # 1-8 for a-h
            for rank in range(1, 9):  # 1-8 for ranks
                expected_square = chr(ord('a') + file - 1) + str(rank)
                
                initial_state = {
                    "stack": [],
                    "x": f"int{file-1:010b}",
                    "y": f"int{rank-1:010b}"
                }
                
                expected_state = {
                    "stack": [expected_square],
                    "x": f"int{file-1:010b}",
                    "y": f"int{rank-1:010b}"
                }
                
                result = execute_instruction(initial_state, intxy_to_location("x", "y"))
                self.assertStateEqual(result, expected_state)

    def test_list_pop(self):
        """Test popping items from a semicolon-delimited list"""
        
        # Test case 1: Multiple items in list
        initial = {
            "stack": [],
            "source_list": "first;second;third",
            "dest_var": "old_value"
        }
        expected = {
            "stack": [],
            "source_list": "second;third",
            "dest_var": "first"
        }
        
        result = execute_instruction(initial, list_pop("source_list", "dest_var"))
        self.assertStateEqual(result, expected)
    
        # Test case 2: Single item in list (no semicolons)
        initial = {
            "stack": [],
            "source_list": "only_item;",
            "dest_var": "old_value"
        }
        expected = {
            "stack": [],
            "source_list": "",
            "dest_var": "only_item"
        }
        
        result = execute_instruction(initial, list_pop("source_list", "dest_var"))
        self.assertStateEqual(result, expected)
    
        # Test case 3: Destination variable doesn't exist yet
        initial = {
            "stack": ["baz"],
            "source_list": "first;second;"
        }
        expected = {
            "stack": ["baz"],
            "source_list": "second;",
            "dest_var": "first"
        }
        
        result = execute_instruction(initial, list_pop("source_list", "dest_var"))
        self.assertStateEqual(result, expected)

    def test_boolean_and(self):
        """Test AND operation for all combinations, preserving stack and variables"""
        test_cases = [
            (True, True, True),   # a AND b = result
            (True, False, False),
            (False, True, False),
            (False, False, False)
        ]
        
        for a, b, expected_result in test_cases:
            with self.subTest(f"{a} AND {b} = {expected_result}"):
                # Setup initial state with extra stack items and variables
                initial = {
                    "stack": [str(b), str(a), "preserve_me"],
                    "test_var": "original_value",
                    "other_var": "unchanged"
                }
                
                # Expected state should preserve other stack items and variables
                expected = {
                    "stack": [str(expected_result), "preserve_me"],
                    "test_var": "original_value",
                    "other_var": "unchanged"
                }
                
                result = execute_instruction(initial, boolean_and())
                self.assertStateEqual(result, expected)
    
    def test_boolean_or(self):
        """Test OR operation for all combinations, preserving stack and variables"""
        test_cases = [
            (True, True, True),   # a OR b = result
            (True, False, True),
            (False, True, True),
            (False, False, False)
        ]
        
        for a, b, expected_result in test_cases:
            with self.subTest(f"{a} OR {b} = {expected_result}"):
                # Setup initial state with extra stack items and variables
                initial = {
                    "stack": [str(b), str(a), "keep_this_value"],
                    "some_var": "test_value",
                    "another_var": "should_not_change"
                }
                
                # Expected state should preserve other stack items and variables
                expected = {
                    "stack": [str(expected_result), "keep_this_value", ],
                    "some_var": "test_value",
                    "another_var": "should_not_change"
                }
                
                result = execute_instruction(initial, boolean_or())
                self.assertStateEqual(result, expected)        

    def test_variable_uniq(self):
        """Test removing duplicates from a semicolon-delimited list while preserving order.
        Lists always end with a semicolon followed by newline."""
        
        test_cases = [
            # Basic case with duplicates
            {
                "initial": {
                    "stack": [],
                    "test_list": "a;b;b;b;c;c;d;"
                },
                "expected": {
                    "stack": [],
                    "test_list": "a;b;c;d;"
                }
            },
            # No duplicates case
            {
                "initial": {
                    "stack": [],
                    "test_list": "a;b;c;d;"
                },
                "expected": {
                    "stack": [],
                    "test_list": "a;b;c;d;"
                }
            },
            # Multiple consecutive duplicates
            {
                "initial": {
                    "stack": [],
                    "test_list": "x;x;x;x;y;y;y;z;"
                },
                "expected": {
                    "stack": [],
                    "test_list": "x;y;z;"
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(f"Case {i}"):
                result = execute_instruction(
                    test_case["initial"], 
                    variable_uniq("test_list")
                )
                self.assertStateEqual(result, test_case["expected"])

    def test_delete_var(self):
        """Test deleting a variable from the state"""
        
        test_cases = [
            # Basic case - delete middle variable
            {
                "initial": {
                    "stack": ["value1"],
                    "keep1": "test1",
                    "delete_me": "remove",
                    "keep2": "test2"
                },
                "expected": {
                    "stack": ["value1"],
                    "keep1": "test1",
                    "keep2": "test2"
                },
                "var_to_delete": "delete_me"
            },
            # Delete last variable
            {
                "initial": {
                    "stack": [],
                    "a": "keep",
                    "b": "also_keep",
                    "last": "remove"
                },
                "expected": {
                    "stack": [],
                    "a": "keep",
                    "b": "also_keep"
                },
                "var_to_delete": "last"
            },
            # Delete first variable (not stack)
            {
                "initial": {
                    "stack": ["preserve"],
                    "first": "remove",
                    "middle": "keep",
                    "end": "keep"
                },
                "expected": {
                    "stack": ["preserve"],
                    "middle": "keep",
                    "end": "keep"
                },
                "var_to_delete": "first"
            },
            # Try to delete non-existent variable
            {
                "initial": {
                    "stack": [],
                    "existing": "keep"
                },
                "expected": {
                    "stack": [],
                    "existing": "keep"
                },
                "var_to_delete": "not_here"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(f"Case {i}"):
                result = execute_instruction(
                    test_case["initial"],
                    delete_var(test_case["var_to_delete"])
                )
                self.assertStateEqual(result, test_case["expected"])                

    def test_isany(self):
        """Test matching stack top against multiple options"""
        
        # Test case 1: Match first option
        initial = {
            "stack": ["a"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["a", "b", "c"]))
        self.assertStateEqual(result, expected)
        
        # Test case 2: Match middle option
        initial = {
            "stack": ["b"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["a", "b", "c"]))
        self.assertStateEqual(result, expected)
        
        # Test case 3: Match last option
        initial = {
            "stack": ["c"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["a", "b", "c"]))
        self.assertStateEqual(result, expected)
        
        # Test case 4: No match
        initial = {
            "stack": ["d"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["False"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["a", "b", "c"]))
        self.assertStateEqual(result, expected)
        
        # Test case 6: Single option
        initial = {
            "stack": ["x"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["x"]))
        self.assertStateEqual(result, expected)
        
        # Test case 7: Match with special characters
        initial = {
            "stack": ["test.123"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["test.123", "other"]))
        self.assertStateEqual(result, expected)
        
        # Test case 8: Preserve rest of stack
        initial = {
            "stack": ["a", "keep1", "keep2"],
            "other_var": "preserve"
        }
        expected = {
            "stack": ["True", "keep1", "keep2"],
            "other_var": "preserve"
        }
        result = execute_instruction(initial, isany(["a", "b", "c"]))
        self.assertStateEqual(result, expected)

    def test_piece_value(self):
        """Test piece value calculations for various board positions with +100 offsets."""
        
        def run_test(fen: str, expected_value: int):
            """Helper to run a single piece value test."""
            state = {"stack": [fen]}
    
            # Execute piece_value operation
            state = execute_instruction(state, piece_value())
            
            # Convert result back from unary
            final_state = execute_instruction(state, from_unary())
            
            # Expected value should be formatted as int with 3 digits
            expected_state = {"stack": [f"int{expected_value:010b}"]}
            self.assertStateEqual(final_state, expected_state)
        
        test_cases = [
            # 1) Empty board
            ("8/8/8/8/8/8/8/8", 100),
            
            # 2) Starting position
            ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", 100),
            
            # 3) Just kings
            ("4k3/8/8/8/8/8/8/4K3", 100),
            
            # 4) Single white pawn
            ("4k3/8/8/8/8/8/P7/4K3", 101),
            
            # 5) Single black pawn
            ("4k3/p7/8/8/8/8/8/4K3", 99),
            
            # 6) White queen vs black rook (fixed!)
            ("4kr2/8/8/8/3Q4/8/8/4K3", 104),
            
            # 7) Complex position with multiple pieces (fixed!)
            ("4k3/8/2p1p3/3Q4/4n3/2P5/5P2/4K3", 106),
            
            # 8) All white major pieces, no black (fixed!)
            ("k7/8/8/8/8/8/8/RNBQKBR1", 128),
            
            # 9) All black major pieces, no white (fixed!)
            ("rbqkbnr1/8/8/8/8/8/8/7K", 72),
            
            # 10) Equal material (Q vs Q+R) (fixed example)
            ("2kqr3/8/8/3Q4/8/8/8/K3R3", 100),
            
            # 11) Max white material without pawns (example fix)
            ("8/8/8/8/8/8/R7/RQQQQQQQ", 173),
            
            # 12) Max black material without pawns (example fix)
            ("rqqqqqqq/r7/8/8/8/8/8/8", 27),
            
            # 13) All white pawns
            ("7k/8/8/8/8/8/PPPPPPPP/K7", 108),
            
            # 14) All black pawns
            ("7k/pppppppp/8/8/8/8/8/7K", 92),
            
            # 15) Mixed pawn ending
            ("8/ppp5/8/PPP4k/8/8/8/7K", 100),
            
            # 16) Queen vs 3 minor pieces
            ("4k3/8/2nbn3/8/3Q4/8/8/4K3", 100),
            
            # 17) Rooks and knights only
            ("rn3nr/8/8/8/8/8/8/RN3NR", 100),
            
            # 18) Complex middlegame
            ("r1bqk2r/ppp2ppp/2n5/3np3/2B5/5N2/PPP2PPP/RNBQ1RK1", 102),
            
            # 19) Knight vs bishop
            ("4k3/8/8/3n4/4B3/8/8/4K3", 100),
            
            # 20) Multiple queens
            ("4k3/8/8/3QQ3/8/8/8/4K3", 118)
        ]
        
        # Run all test cases
        for i, (fen, expected) in enumerate(test_cases):
            with self.subTest(f"Case {i+1}: {fen}"):
                run_test(fen, (expected-100)*2+200)
            

    def test_is_stack_empty(self):
        """Test checking if stack is empty"""
        
        # Case 1: Truly empty stack with variables after
        initial = {
            "stack": [],
            "var1": "test",
            "var2": "value"
        }
        expected = {
            "stack": ["True"],
            "var1": "test",
            "var2": "value"
        }
        result = execute_instruction(initial, is_stack_empty())
        self.assertStateEqual(result, expected)
    
        # Case 2: Empty stack with no variables
        initial = {
            "stack": []
        }
        expected = {
            "stack": ["True"]
        }
        result = execute_instruction(initial, is_stack_empty())
        self.assertStateEqual(result, expected)
    
        # Case 3: Single item on stack
        initial = {
            "stack": ["item1"],
            "var": "test"
        }
        expected = {
            "stack": ["False", "item1"],
            "var": "test"
        }
        result = execute_instruction(initial, is_stack_empty())
        self.assertStateEqual(result, expected)
        
        # Case 4: Multiple items on stack
        initial = {
            "stack": ["top", "middle", "bottom"],
            "var": "test"
        }
        expected = {
            "stack": ["False", "top", "middle", "bottom"],
            "var": "test"
        }
        result = execute_instruction(initial, is_stack_empty())
        self.assertStateEqual(result, expected)            

    def test_castle_rights(self):
        """Test castling rights are removed if pieces aren't on correct squares"""
    
        # Test white kingside castling - only allowed if K on e1 and R on h1
        initial = {
            "stack": ["8/8/8/8/8/8/8/4K2R w KQkq -"],
        }
        expected = {
            "stack": ["8/8/8/8/8/8/8/4K2R w K -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test both white castling rights - King on e1 with both rooks
        initial = {
            "stack": ["8/8/8/8/8/8/8/R3K2R w KQkq -"],
        }
        expected = {
            "stack": ["8/8/8/8/8/8/8/R3K2R w KQ -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test both black castling rights - King on e8 with both rooks
        initial = {
            "stack": ["r3k2r/8/8/8/8/8/8/8 w KQkq -"],
        }
        expected = {
            "stack": ["r3k2r/8/8/8/8/8/8/8 w kq -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test all castling rights - Both kings with their rooks
        initial = {
            "stack": ["r3k2r/8/8/8/8/8/8/R3K2R w KQkq -"],
        }
        expected = {
            "stack": ["r3k2r/8/8/8/8/8/8/R3K2R w KQkq -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test white queenside castling - only allowed if K on e1 and R on a1
        initial = {
            "stack": ["8/8/8/8/8/8/8/R3K3 w KQkq -"],
        }
        expected = {
            "stack": ["8/8/8/8/8/8/8/R3K3 w Q -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test black kingside castling - only allowed if k on e8 and r on h8
        initial = {
            "stack": ["4k2r/8/8/8/8/8/8/8 w KQkq -"],
        }
        expected = {
            "stack": ["4k2r/8/8/8/8/8/8/8 w k -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)
    
        # Test black queenside castling - only allowed if k on e8 and r on a8
        initial = {
            "stack": ["r3k3/8/8/8/8/8/8/8 w KQkq -"],
        }
        expected = {
            "stack": ["r3k3/8/8/8/8/8/8/8 w q -"],
        }
        result = execute_instruction(initial, expand_chess() + contract_chess())
        self.assertStateEqual(result, expected)

    def test_rook_attacks(self):
        """Test rook attack detection for all squares with rook on h1"""
        
        # Initial position: Rook on h1
        initial_state = """%%
#stack:
#attacked: False
#initial_board: 8/8/8/8/8/8/8/1P5R
"""
    
        # Expected attacked squares are all h-file and first rank squares
        attacked_squares = set()
        # Add all h-file squares
        for rank in '12345678':
            attacked_squares.add('h' + rank)
        # Add all first rank squares
        for file in 'abcdefgh':
            attacked_squares.add(file + '1')
        attacked_squares.remove('h1')
        attacked_squares.remove('a1')
    
        # Test each square
        for file in 'abcdefgh':
            for rank in '12345678':
                square = file + rank
                
                # Generate and apply the regex transformations
                tree = trace(lambda x: is_square_under_attack_by_rook(x, square, color_white))
                linear = linearize_tree(tree)
                args = create(linear)
                
                # Apply transformations
                state = initial_state
                for op, regexs in args:
                    for pattern, repl in regexs:
                        state = re.sub(pattern, repl, state)
    
                # Extract final state
                cpu_state = CPUState.from_string(state)
                
                # Check if square is correctly identified as attacked or not
                expected = str(square in attacked_squares)
                actual = cpu_state.variables["attacked"]
                
                assert actual == expected, \
                    f'Failed for square {square}: expected {expected}, got {actual}'
        

    def test_bishop_attacks(self):
        """Test bishop attack detection for all squares with bishop on e4"""
        
        # Initial position: Bishop on e4
        initial_state = """%%
#stack:
#attacked: False
#initial_board: 8/8/8/8/4B3/8/6P1/8
"""

        
        attacked_squares = set([
            # Northeast diagonal
        'f5', 'g6', 'h7',
            # Southeast diagonal 
        'f3', 'g2',
            # Southwest diagonal
        'd3', 'c2', 'b1',
            # Northwest diagonal
            'd5', 'c6', 'b7', 'a8'
        ])
    
        # Test each square
        for file in 'abcdefgh':
            for rank in '12345678':
                square = file + rank
                
                # Generate and apply the regex transformations
                tree = trace(lambda x: is_square_under_attack_by_bishop(x, square, color_white))
                linear = linearize_tree(tree)
                args = create(linear)
                
                # Apply transformations
                state = initial_state
                for op, regexs in args:
                    for pattern, repl in regexs:
                        state = re.sub(pattern, repl, state)
    
                # Extract final state
                cpu_state = CPUState.from_string(state)
                
                # Check if square is correctly identified as attacked or not
                expected = str(square in attacked_squares)
                actual = cpu_state.variables["attacked"]
                
                assert actual == expected, \
                    f'Failed for square {square}: expected {expected}, got {actual}'
        

    def test_pawn_attacks(self):
        """Test pawn attack detection for all squares with pawn on e4"""
        
        # Initial position: White pawn on e4
        initial_state = """%%
#stack:
#attacked: False
#initial_board: 8/8/8/8/4P3/8/8/8
"""
    
        # Expected attacked squares - just the two diagonal squares in front
        attacked_squares = set([
            'd5',  # Up-left diagonal
            'f5'   # Up-right diagonal
        ])
    
        # Test each square
        for file in 'abcdefgh':
            for rank in '12345678':
                square = file + rank
                
                # Generate and apply the regex transformations
                tree = trace(lambda x: is_square_under_attack_by_pawn(x, square, color_white))
                linear = linearize_tree(tree)
                args = create(linear)
                
                # Apply transformations
                state = initial_state
                for op, regexs in args:
                    for pattern, repl in regexs:
                        state = re.sub(pattern, repl, state)
    
                # Extract final state
                cpu_state = CPUState.from_string(state)
                
                # Check if square is correctly identified as attacked or not
                expected = str(square in attacked_squares)
                actual = cpu_state.variables["attacked"]
                
                assert actual == expected, \
                    f'Failed for square {square}: expected {expected}, got {actual}'
        
    
        # Let's also test black pawn attacks
        black_initial_state = """%%
#stack:
#attacked: False
#initial_board: 8/8/8/8/4p3/8/8/8
"""
    
        # Black pawn on e4 attacks d3 and f3
        black_attacked_squares = set([
            'd3',  # Down-left diagonal
            'f3'   # Down-right diagonal
        ])
    
        # Test each square for black pawn
        for file in 'abcdefgh':
            for rank in '12345678':
                square = file + rank
                
                # Generate and apply the regex transformations
                tree = trace(lambda x: is_square_under_attack_by_pawn(x, square, color_black))
                linear = linearize_tree(tree)
                args = create(linear)
                
                # Apply transformations
                state = black_initial_state
                for op, regexs in args:
                    for pattern, repl in regexs:
                        state = re.sub(pattern, repl, state)
    
                # Extract final state
                cpu_state = CPUState.from_string(state)
                
                # Check if square is correctly identified as attacked or not
                expected = str(square in black_attacked_squares)
                actual = cpu_state.variables["attacked"]
                
                assert actual == expected, \
                    f'Failed for square {square}: expected {expected}, got {actual}'
        
        print("All black pawn squares tested successfully!")



    def test_keep_only_min_thread(self):
        """Test keeping only the thread with the minimum number of 'A's."""
        

        import random
        random.seed(42)  # For reproducibility
        
        def generate_test_case():
            # Generate between 2 and 5 threads
            num_threads = random.randint(2, 5)
            
            # Generate lengths for each thread (0-20 As)
            lengths = [random.randint(1, 30) for _ in range(num_threads)]
            min_length = min(lengths)
            
            # Create threads
            threads = []
            for length in lengths:
                # Sometimes add other characters
                thread = 'A' * length
                threads.append('#stack:\n' + thread)
            
            # Create input string
            input_str = '%%\n' + '\n%%\n'.join(threads) + '\n'
            
            # Find the first thread with minimum number of As
            min_thread = min(threads, key=lambda x: x.count('A'))
            expected = f'%%\n{min_thread}\n'

            return input_str, expected
        
        test_cases = [generate_test_case() for _ in range(100)]
        
        for input_str, expected in test_cases:
            # Generate and apply the regex transformations
            args = keep_only_max_thread() + keep_only_first_thread()
            
            # Apply transformations
            result = input_str
            for pattern, repl in args:
                result = re.sub(pattern, repl, result)
            
            self.assertEqual(result, expected, 
                f"Failed for input:\n{input_str}\nExpected:\n{expected}\nGot:\n{result}")
                    

import chess
import re


def calculate_moves(board_state, piece_function, color_function):
    """
    Calculate legal moves for a given piece on a board state.
    
    Args:
        board_state (str): FEN-like string representing the board state
        piece_function: Function that calculates moves for a specific piece
        color_function: Color function (color_white or color_black)
    
    Returns:
        str: Resulting board state after calculating all legal moves
    """
    # Initialize the state with the board
    state = f'%%\n#stack:\n#initial_board: {board_state}\n'
    
    # Generate and linearize the move tree
    tree = trace(lambda x: piece_function(x, color_function))
    linear = linearize_tree(tree)
    args = create(linear)
    
    # Apply each operation to transform the state
    for op, regexs in args:
        for pattern, repl in regexs:
            state = re.sub(pattern, repl, state)
            # Safety check for malformed states
            if '#' in state.replace("\n#", ""):
                raise ValueError("Invalid state generated during move calculation")
                
    return state

def extract_legal_moves(state_str):
    """Extract the legal moves from the state string, ignoring color."""
    for line in state_str.split('\n'):
        if line.startswith('#legal'):
            # Split on semicolons and filter out empty strings, removing color
            moves = [move.strip().split()[0] for move in line.split(':')[1].split(';') 
                    if move.strip()]
            return moves
    return []

def fen_to_board_state(fen):
    """Convert full FEN to just the position part."""
    return fen.split()[0]


class ChessBoardTests(unittest.TestCase):
    def _verify_moves(self, pos, piece_function, color_function, piece_type):
        """Helper to verify moves match between our implementation and python-chess."""
        result = calculate_moves(pos, piece_function, color_function)
        our_moves = set(extract_legal_moves(result))
        if color_function == color_black:
            pos = pos.replace('w', 'b')
        
        board = chess.Board(pos + " 0 1")
        python_chess_moves = set()
        for move in board.generate_pseudo_legal_moves():
            if board.piece_type_at(move.from_square) == getattr(chess, piece_type):
                board_copy = board.copy()
                board_copy.push(move)
                python_chess_moves.add(board_copy.board_fen())
        
        # Remove original position from our moves
        original_pos = pos.split()[0]
        our_moves_without_original = our_moves - {original_pos}
        
        self.assertEqual(
            our_moves_without_original, 
            python_chess_moves,
            f"\nPosition: {pos}\nOur moves: {our_moves_without_original}\nPython-chess moves: {python_chess_moves}"
        )

    def test_knight_moves(self):
        test_positions = [
            # Knight in corner
            "8/8/8/8/8/8/8/7N w - -",
            # Knight in center
            "8/8/8/3N4/8/8/8/8 w - -",
            # Knight with friendly pieces blocking
            "8/8/8/3N4/2P1P3/3P4/8/8 w - -",
            # Knight with enemy pieces to capture
            "8/8/8/3N4/2p1p3/3p4/8/8 w - -",
            # Multiple knights
            "8/8/2N5/8/3N4/8/8/8 w - -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, knight_moves, color_white, 'KNIGHT')

    def test_king_moves(self):
        test_positions = [
            # King in corner
            "8/8/8/8/8/8/8/7K w - -",
            # King in center
            "8/8/8/3K4/8/8/8/8 w - -",
            # King with friendly pieces blocking
            "8/8/8/2PPP3/2PKP3/2PPP3/8/8 w - -",
            # King with enemy pieces to capture
            "8/8/8/2ppp3/2pKp3/2ppp3/8/8 w - -",
            # King near enemy king (showing blocked squares)
            "8/8/8/3k4/3K4/8/8/8 w - -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, king_moves, color_white, 'KING')

    def test_queen_moves(self):
        test_positions = [
            # Queen in corner
            "8/8/8/8/8/8/8/7Q w - -",
            # Queen in center
            "8/8/8/3Q4/8/8/8/8 w - -",
            # Queen with friendly pieces blocking
            "8/8/8/2PPP3/2PQP3/2PPP3/8/8 w - -",
            # Queen with enemy pieces to capture
            "8/8/8/2ppp3/2pQp3/2ppp3/8/8 w - -",
            # Queen with mixed blocking and captures
            "8/8/1p6/3Q4/5P2/8/8/8 w - -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, queen_moves, color_white, 'QUEEN')

    def test_rook_moves(self):
        test_positions = [
            # Rook in corner
            "8/8/8/8/8/8/8/7R w - -",
            # Rook in center
            "8/8/8/3R4/8/8/8/8 w - -",
            # Rook with friendly pieces blocking
            "8/8/8/2P1P3/3R4/2P1P3/8/8 w - -",
            # Rook with enemy pieces to capture
            "8/8/8/2p1p3/3R4/2p1p3/8/8 w - -",
            # Multiple rooks
            "8/8/2R5/8/3R4/8/8/8 w - -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, rook_moves, color_white, 'ROOK')

    def test_bishop_moves(self):
        test_positions = [
            # Bishop in corner
            "8/8/8/8/8/8/8/7B w - -",
            # Bishop in center
            "8/8/8/3B4/8/8/8/8 w - -",
            # Bishop with friendly pieces blocking
            "8/8/2P3P1/8/3B4/8/2P3P1/8 w - -",
            # Bishop with enemy pieces to capture
            "8/8/2p3p1/8/3B4/8/2p3p1/8 w - -",
            # Multiple bishops
            "8/8/2B5/8/3B4/8/8/8 w - -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, bishop_moves, color_white, 'BISHOP')

    def test_pawn_moves(self):
        test_positions = [
            # Pawn on starting square
            "8/8/8/8/8/8/4P3/8 w - -",
            # Pawn in middle of board
            "8/8/8/8/4P3/8/8/8 w - -",
            # Pawn with captures available
            "8/8/8/3p1p2/4P3/8/8/8 w - -",
            # Pawn blocked by friendly piece
            "8/8/8/4P3/4P3/8/8/8 w - -",
            # Pawn blocked by opponent piece
            "8/8/8/4p3/4P3/8/8/8 w - -",
            # Multiple pawns
            "8/8/8/8/8/8/2P1P3/8 w - -",
            "rnbqkbnr/1ppppppp/8/p7/P7/8/1PPPPPPP/RNBQKBNR w KQkq -"
        ]
        for pos in test_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, pawn_moves, color_white, 'PAWN')
                self._verify_moves(pos, pawn_moves, color_black, 'PAWN')


    def test_pawn_moves_en_passant(self):
        """
        Tests specifically for en passant captures. Each FEN sets up an en passant
        target square so that White can capture en passant immediately.
        """
        ep_positions = [
            # 1) Simple EP on adjacent files (d5 vs. e5)
            "8/8/8/3Pp3/8/8/8/8 w - e6",

            # 2) EP capture from the g-file (g5 vs. f5)
            "8/8/8/5pP1/8/8/8/8 w - f6",

            # 3) EP capture from the c-file (c5 vs. b5)
            "8/8/8/1pP5/8/8/8/8 w - b6",

            # 4) EP with multiple White pawns on the board
            "8/2p5/8/3Pp3/8/8/2P1P3/8 w - e6",

            "8/8/8/PPp5/8/8/7P/8 w K c6"
        ]

        for pos in ep_positions:
            with self.subTest(position=pos):
                self._verify_moves(pos, pawn_moves, color_white, 'PAWN')                

    def test_combined_attacks(self):
        """Test attack detection for complex positions against python-chess"""
        
        test_positions = [
            # Original test position
            "7Q/8/3N3R/6N1/K3Pn2/2q1B1k1/3R4/8",
            
            # Simple positions
            "8/8/8/8/4Q3/8/8/8",  # Single queen in center
            "8/8/8/3B4/4N3/8/8/8",  # Bishop and knight
            
            # Complex positions
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQK2R",  # Development position
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R",  # Complex middlegame
            "8/3K4/2p5/p2b2r1/5k2/8/8/1q6",  # Endgame position
            "2r3k1/p4p2/3Rp2p/1p2P1pK/8/1P4P1/P4P2/8",  # Rook endgame
            "6k1/5ppp/8/8/8/8/1B6/K7",  # Simple bishop vs king
            "4k3/8/3Q4/8/4P3/8/8/4K3",  # Queen and pawn
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"  # Starting position
        ]
        
        for fen in test_positions:
            # Create initial state with the FEN position
            initial_state = f"""%%
#stack:
#initial_board: {fen}
"""
            
            # Get attacked squares from python-chess
            board = chess.Board(f"{fen} w - - 0 1")
            expected_squares = set()
            for square in chess.SQUARES:
                if board.is_attacked_by(chess.WHITE, square):
                    square_name = chess.square_name(square)
                    expected_squares.add(square_name)
                    
            # Test each square
            for file in 'abcdefgh':
                for rank in '12345678':
                    square = file + rank
                    
                    # Generate and apply the regex transformations
                    tree = trace(lambda x: is_square_under_attack(x, square, color_white))
                    linear = linearize_tree(tree)
                    args = create(linear)
                    
                    # Apply transformations
                    state = initial_state
                    for op, regexs in args:
                        for pattern, repl in regexs:
                            state = re.sub(pattern, repl, state)
    
                    # Extract final state
                    cpu_state = CPUState.from_string(state)
                    
                    # Check if square is correctly identified as attacked or not
                    expected = str(square in expected_squares)
                    actual = cpu_state.variables["attacked"]
                    
                    assert actual == expected, \
                        f'Failed for FEN {fen}, square {square}: expected {expected}, got {actual}'        

                
def run_tests():
    unittest.main(argv=[''], verbosity=2, exit=False)

if __name__ == '__main__':
    run_tests()

