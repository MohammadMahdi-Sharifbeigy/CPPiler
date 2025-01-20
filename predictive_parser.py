from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from collections import deque

@dataclass
class ParseTreeNode:
    value: str
    children: List['ParseTreeNode']
    parent: Optional['ParseTreeNode'] = None
    token_type: Optional[str] = None
    token_value: Optional[str] = None

class PredictiveParser:
    def __init__(self, parser_tables):
        self.parser_tables = parser_tables
        self.token_stream = []
        self.current_token_idx = 0
        self.parse_tree_root = None
        self.current_position = 0
        self.symbol_map = {
            '(': 'lparen',
            ')': 'rparen',
            '{': 'lbrace',
            '}': 'rbrace',
            ';': 'semicolon',
            ',': 'comma',
            '=': 'assign',
            '+': 'plus',
            '-': 'minus',
            '*': 'multiply',
            '>=': 'gteq',
            '<=': 'lteq',
            '==': 'equal',
            '!=': 'notequal',
            '>>': 'input',
            '<<': 'output'
        }
        self.error_handler = ErrorHandler()

    def get_terminal_symbol(self, token_type: str, token_value: str) -> str:
        """Convert token to terminal symbol."""
        # Handle #include as a special case
        if token_type == 'symbol' and token_value == '#':
            # Look ahead to check if next token is 'include'
            next_idx = self.current_token_idx + 1
            if next_idx < len(self.token_stream):
                next_type, next_value, _ = self.token_stream[next_idx]
                if next_type == 'reservedword' and next_value == 'include':
                    self.current_token_idx += 1  # Skip the include token
                    return '#include'
            return None  # Skip '#' if not followed by include
        
        # Handle symbols
        if token_type == 'symbol':
            # Check for '<' to match <LibName> pattern
            if token_value == '<':
                prev_idx = self.current_token_idx - 1
                if prev_idx >= 0:
                    next_idx = self.current_token_idx + 1
                    if next_idx < len(self.token_stream) and next_idx + 1 < len(self.token_stream):
                        lib_type, lib_value, _ = self.token_stream[next_idx]
                        close_type, close_value, _ = self.token_stream[next_idx + 1]
                        
                        # Check if we have a valid library name followed by '>'
                        is_valid_lib = (lib_value == 'iostream' or lib_type == 'identifier')
                        
                        if is_valid_lib and close_type == 'symbol' and close_value == '>':
                            self.current_token_idx += 2  # Skip library name and '>'
                            return '<LibName>'
            
            # Input/output operators
            if token_value in ['<<', '>>']:
                return token_value
                
            # Comparison operators    
            if token_value in ['<=', '>=', '==', '!=']:
                return token_value
                
            # Single operators
            if token_value in ['<', '>']:
                # Check if it's not part of a compound operator
                next_idx = self.current_token_idx + 1
                if next_idx < len(self.token_stream):
                    next_type, next_value, _ = self.token_stream[next_idx]
                    if next_type == 'symbol' and next_value == token_value:
                        return None  # Skip single operator if part of compound
                return token_value
        
        # Handle basic types and reserved words
        # Handle strings, numbers and identifiers
        if token_type in ['string', 'number', 'identifier']:
            return token_type
            
        # Handle reserved words
        if token_type == 'reservedword':
            return token_value
        
        return token_value

    def parse(self, tokens: List[Tuple[str, str, int]], source_code: str) -> 'ParseTreeNode':
        """Parse the input tokens using the parsing table."""
        self.token_stream = tokens
        self.current_token_idx = 0
        self.last_was_hash = False
        
        self.error_handler.initialize_source(source_code)
        
        if not self.error_handler.line_positions:
            self.error_handler.line_positions = [0]
        
        self.parse_tree_root = ParseTreeNode('Start', [], None)
        
        # Initialize stack with start symbol and end marker
        stack = deque(['$', 'Start'])
        current_node = self.parse_tree_root
        node_stack = deque([current_node])  # Keep track of nodes corresponding to stack symbols
        
        while stack and self.current_token_idx < len(self.token_stream):
            top = stack[-1]
            token_type, token_value, position = self.token_stream[self.current_token_idx]
            terminal = self.get_terminal_symbol(token_type, token_value)
            
            # Skip this token if it returned None like standalone '#'
            if terminal is None:
                self.current_token_idx += 1
                continue
            
            if top == '$' and terminal == '$':
                return self.parse_tree_root
                
            if top == terminal:  # Match terminal
                stack.pop()
                current_node = node_stack.pop()
                current_node.token_type = token_type
                current_node.token_value = token_value
                self.current_token_idx += 1
            elif top not in self.parser_tables.grammar:  # Terminal on top, but no match
                error_message = f"Unexpected token '{token_value}'. Expected {top}"
                self.error_handler.handle_syntax_error(token_value, top, position)
            else:  # Non-terminal on top
                try:
                    production = self.parser_tables.get_parse_table_entry(top, terminal)
                except ValueError as e:
                    error_message = f"Unexpected symbol '{token_value}' after '{top}'"
                    self.error_handler.handle_syntax_error(token_value, "", position)
                
                if not production:
                    context = self._get_parsing_context(top)
                    error_message = (f"Syntax error at '{token_value}'. "
                                f"Expected one of: {', '.join(context)}")
                    self.error_handler.handle_syntax_error(token_value, context, position)
                    
                stack.pop()
                node_stack.pop()  # Remove current non-terminal node from node stack
                
                if production != 'ε':
                    symbols = production.split()
                    # Add symbols to stack in reverse order
                    for symbol in reversed(symbols):
                        stack.append(symbol)
                        new_node = ParseTreeNode(symbol, [], current_node)
                        current_node.children.append(new_node)
                        node_stack.append(new_node)  # Add new node to node stack
                    
                    if current_node.children:
                        current_node = current_node.children[0]
        
        if stack and stack[-1] != '$':
            last_token = self.token_stream[self.current_token_idx - 1]
            error_message = f"Unexpected end of input. Expected {stack[-1]}"
            self.error_handler.handle_syntax_error(last_token[1], stack[-1], last_token[2])
            
        return self.parse_tree_root

    def _get_parsing_context(self, non_terminal: str) -> List[str]:
        """Get the list of possible terminals that could appear after the given non-terminal."""
        context = set()
        
        # Get all terminals that have productions for this non-terminal
        for terminal in self.parser_tables.terminals:
            if self.parser_tables.parse_table[non_terminal].get(terminal):
                context.add(terminal)
                
        return sorted(list(context))

    def get_production_sequence(self) -> List[str]:
        """Return the sequence of productions used in parsing."""
        def traverse_tree(node: ParseTreeNode) -> List[str]:
            if not node.children:
                return []
            
            productions = []
            production = f"{node.value} -> "
            
            # Handle leaf nodes (tokens)
            if node.token_type and node.token_value:
                production += f"{node.token_type}({node.token_value})"
            else:
                production += " ".join(child.value for child in node.children)
            
            productions.append(production)
            
            for child in node.children:
                productions.extend(traverse_tree(child))
                
            return productions
        
        return traverse_tree(self.parse_tree_root)

class ErrorHandler:
    def __init__(self):
        self.errors = []
        self.source_code = ""
        self.line_positions = []
        self.current_position = 0

    def initialize_source(self, source_code: str):
        """Initialize with source code and compute line positions."""
        self.source_code = source_code
        self.line_positions = [0]
        
        for i, char in enumerate(source_code):
            if char == '\n':
                self.line_positions.append(i + 1)
                
    def get_line_number(self, position: int) -> int:
        """Get line number for a given position in the source."""
        for line_num, start_pos in enumerate(self.line_positions, 1):
            if position < start_pos:
                return line_num - 1
        return len(self.line_positions)
        
    def get_column_number(self, position: int) -> int:
        """Get column number for a given position in the source."""
        line_num = self.get_line_number(position)
        line_start = self.line_positions[line_num - 1]
        return position - line_start + 1

    def get_line_content(self, line_number: int) -> str:
        """Get the content of a specific line."""
        if line_number < 1 or line_number > len(self.line_positions):
            return ""
            
        start = self.line_positions[line_number - 1]
        end = (self.line_positions[line_number] 
               if line_number < len(self.line_positions) 
               else len(self.source_code))
               
        return self.source_code[start:end].rstrip('\n')

    def handle_syntax_error(self, token_value: str, expected_value: str, position: int):
        """Handle syntax error with detailed information."""
        if isinstance(expected_value, list):
            message = f"Syntax Error: Unexpected '{token_value}'. Expected one of: {', '.join(expected_value)}"
        else:
            message = f"Syntax Error: Expected '{expected_value}', found '{token_value}'"
            
        error_msg = self.format_error(position, message)
        raise SyntaxError(error_msg)

    def format_error(self, position: int, message: str) -> str:
        """Format error message with line number, column number, and context."""
        line_number = self.get_line_number(position)
        column = self.get_column_number(position)
        line_content = self.get_line_content(line_number)
        
        error_msg = [
            f"\nError at line {line_number}, column {column}:",
            message,
            "\nContext:",
        ]
        
        start_line = max(1, line_number - 2)
        end_line = min(len(self.line_positions), line_number + 2)
        
        for i in range(start_line, end_line + 1):
            line_text = self.get_line_content(i)
            prefix = "-> " if i == line_number else "   "
            error_msg.append(f"{prefix}{i:4d} | {line_text}")
            if i == line_number:
                error_msg.append("      " + " " * (column - 1) + "^")
                
        return "\n".join(error_msg)

    def handle_missing_semicolon(self, position: int):
        """Handle missing semicolon error."""
        message = "Missing semicolon at end of statement"
        error_msg = self.format_error(position, message)
        raise SyntaxError(error_msg)

    def handle_invalid_assignment(self, position: int):
        """Handle invalid assignment error."""
        message = "Invalid left-hand side in assignment"
        error_msg = self.format_error(position, message)
        raise SyntaxError(error_msg)

    def check_syntax(self, token_stream, source_code: str) -> bool:
        """Check for basic syntax errors in the token stream."""
        self.initialize_source(source_code)
        last_token = None
        in_statement = False
        
        for token_type, token_value, position in token_stream:
            if last_token:
                last_type, last_value, last_pos = last_token
                
                # Start of a new statement
                if last_value in [';', '{', '}']:
                    in_statement = False
                
                # Check for missing semicolon
                if in_statement and last_type in ['identifier', 'number']:
                    # Allow these tokens after identifier/number
                    allowed_follows = {
                        ';',  # End of statement
                        ',',  # List continuation
                        '=',  # Assignment
                        '+', '-', '*', '/', # Arithmetic operators  
                        '>=', '<=', '==', '!=', # Comparison operators
                        ')', ']',  # Closing brackets
                        '<<', '>>'  # Stream operators
                    }
                    
                    if token_value not in allowed_follows:
                        self.handle_missing_semicolon(last_pos)
                
                # Check for invalid assignment
                if token_value == '=' and last_type not in ['identifier']:
                    self.handle_invalid_assignment(position)
                
                # Track statement context
                if token_value in ['(', '{']:
                    in_statement = False
                elif token_value not in [';', '}']:
                    in_statement = True
            
            last_token = (token_type, token_value, position)
            
        return True

class TreeSearcher:
    def __init__(self, parse_tree_root: ParseTreeNode):
        self.root = parse_tree_root
        
    def find_identifier_definition(self, identifier: str) -> Optional[str]:
        """Find the first definition of an identifier in the parse tree."""
        def dfs(node: ParseTreeNode) -> Optional[str]:
            if (node.value == 'identifier' and node.token_value == identifier):
                current = node
                definition = []
                while current and current.value != 'T':
                    if current.token_value:
                        definition.insert(0, current.token_value)
                    else:
                        definition.insert(0, current.value)
                    current = current.parent
                return " ".join(definition)
            
            for child in node.children:
                result = dfs(child)
                if result:
                    return result
            
            return None
        
        return dfs(self.root)