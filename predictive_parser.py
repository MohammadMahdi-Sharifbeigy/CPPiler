from typing import List, Optional, Tuple
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

    def get_terminal_symbol(self, token_type: str, token_value: str) -> str:
        """Convert token to terminal symbol."""
        if token_type == 'symbol' and token_value == '#':
            next_idx = self.current_token_idx + 1
            if next_idx < len(self.token_stream):
                next_type, next_value = self.token_stream[next_idx]
                if next_type == 'reservedword' and next_value == 'include':
                    self.current_token_idx += 1
                    return '#include'
            return None
        
        if token_type == 'symbol':
            if token_value in ['<<', '>>', '>=', '<=', '==', '!=']:
                return token_value
            return token_value
            
        if token_type == 'identifier':
            return 'identifier'
        elif token_type == 'number':
            return 'number'
        elif token_type == 'string':
            return 'string'
        elif token_type == 'reservedword':
            return token_value
            
        return token_value

    def parse(self, tokens: List[Tuple[str, str]]) -> ParseTreeNode:
        """Parse the input tokens using the parsing table."""
        self.token_stream = tokens
        self.current_token_idx = 0
        self.last_was_hash = False
        
        self.parse_tree_root = ParseTreeNode('Start', [], None)
        
        # Initialize stack with start symbol and end marker
        stack = deque(['$', 'Start'])
        current_node = self.parse_tree_root
        
        while stack and self.current_token_idx < len(self.token_stream):
            top = stack[-1]
            token_type, token_value = self.token_stream[self.current_token_idx]
            terminal = self.get_terminal_symbol(token_type, token_value)
            
            if terminal is None:
                self.current_token_idx += 1
                continue
            
            if top == '$' and terminal == '$':
                return self.parse_tree_root
                
            if top == terminal:
                stack.pop()
                current_node.token_type = token_type
                current_node.token_value = token_value
                self.current_token_idx += 1
                current_node = current_node.parent
            elif top not in self.parser_tables.grammar:
                raise SyntaxError(
                    f"Expected {top}, found {token_value} (type: {token_type})"
                )
            else:  # Non-terminal on top
                try:
                    production = self.parser_tables.get_parse_table_entry(top, terminal)
                except ValueError as e:
                    raise SyntaxError(
                        f"Parse error at token '{token_value}': {str(e)}"
                    )
                
                if not production:
                    raise SyntaxError(
                        f"No production rule for {top} with input {terminal}"
                    )
                    
                stack.pop()
                if production != 'ε':
                    symbols = production.split()
                    # Add symbols to stack in reverse order
                    for symbol in reversed(symbols):
                        stack.append(symbol)
                        
                    # Create nodes for all symbols in production
                    for symbol in symbols:
                        new_node = ParseTreeNode(symbol, [], current_node)
                        current_node.children.append(new_node)
                    
                    # Move to first child for next iteration
                    if current_node.children:
                        current_node = current_node.children[0]
                
        if stack and stack[-1] != '$':
            raise SyntaxError(f"Unexpected end of input, expected {stack[-1]}")
            
        return self.parse_tree_root

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
        self.current_line = 1
        self.line_positions = []
        self.source_code = ""
        
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
    
    def get_line_content(self, line_number: int) -> str:
        """Get the content of a specific line."""
        if line_number < 1 or line_number > len(self.line_positions):
            return ""
        
        start = self.line_positions[line_number - 1]
        end = (self.line_positions[line_number] 
               if line_number < len(self.line_positions) 
               else len(self.source_code))
        
        return self.source_code[start:end].rstrip('\n')
    
    def format_error(self, position: int, message: str) -> str:
        """Format error message with line number, line content, and error pointer."""
        line_number = self.get_line_number(position)
        line_content = self.get_line_content(line_number)
        
        line_start = self.line_positions[line_number - 1]
        column = position - line_start
        
        error_msg = [
            f"Error at line {line_number}, column {column + 1}:",
            message,
            line_content,
            " " * column + "^"
        ]
        
        if line_number > 1:
            prev_line = self.get_line_content(line_number - 1)
            error_msg.insert(2, prev_line)
        if line_number < len(self.line_positions):
            next_line = self.get_line_content(line_number + 1)
            error_msg.insert(-1, next_line)
            
        return "\n".join(error_msg)
    
    def handle_error(self, position: int, message: str):
        """Handle an error by formatting it with context and raising an exception."""
        error_message = self.format_error(position, message)
        raise SyntaxError(error_message)
    
    def check_syntax(self, token_stream, source_code: str) -> bool:
        """Check for basic syntax errors."""
        self.initialize_source(source_code)
        valid = True
        last_token = None
        position = 0
        
        for token_type, token_value, token_position in token_stream:
            if token_value == '\n':
                self.current_line += 1
                continue
                
            if last_token:
                last_type, last_value, last_pos = last_token
                if (last_type in ['identifier', 'number'] and 
                    token_value != ';' and token_value != ','):
                    self.handle_error(
                        last_pos,
                        f"Missing semicolon after '{last_value}'"
                    )
                    valid = False
                
                if (token_value == '=' and last_type not in 
                    ['identifier', 'reservedword']):
                    self.handle_error(
                        token_position,
                        f"Invalid left-hand side in assignment"
                    )
                    valid = False
            
            last_token = (token_type, token_value, token_position)
            position = token_position
            
        return valid

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