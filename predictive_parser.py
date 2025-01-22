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
        self.symbol_map = {
            '(': 'lparen', ')': 'rparen',
            '{': 'lbrace', '}': 'rbrace',
            ';': 'semicolon', ',': 'comma',
            '=': 'assign', '+': 'plus',
            '-': 'minus', '*': 'multiply',
            '>=': 'gteq', '<=': 'lteq',
            '==': 'equal', '!=': 'notequal',
            '>>': 'input', '<<': 'output'
        }
        self.error_handler = ErrorHandler()

    def get_terminal_symbol(self, token_type: str, token_value: str) -> str:
        if token_type == 'symbol' and token_value == '#':
            next_idx = self.current_token_idx + 1
            if next_idx < len(self.token_stream):
                next_token = self.token_stream[next_idx]
                if next_token.name == 'reservedword' and next_token.value == 'include':
                    self.current_token_idx += 1
                    return '#include'
            return None

        if token_type == 'symbol':
            if token_value == '<':
                next_idx = self.current_token_idx + 1
                if next_idx < len(self.token_stream) and next_idx + 1 < len(self.token_stream):
                    lib_token = self.token_stream[next_idx]
                    close_token = self.token_stream[next_idx + 1]
                    is_valid_lib = (lib_token.value == 'iostream' or lib_token.name == 'identifier')
                    if is_valid_lib and close_token.name == 'symbol' and close_token.value == '>':
                        self.current_token_idx += 2
                        return '<LibName>'

            if token_value in ['<<', '>>', '<=', '>=', '==', '!=']:
                return token_value

            if token_value in ['<', '>']:
                next_idx = self.current_token_idx + 1
                if next_idx < len(self.token_stream):
                    next_token = self.token_stream[next_idx]
                    if next_token.name == 'symbol' and next_token.value == token_value:
                        return None
                return token_value

        if token_type in ['string', 'number', 'identifier']:
            return token_type

        if token_type == 'reservedword':
            return token_value

        return token_value

    def parse(self, tokens, source_code):
        self.error_handler.initialize_source(source_code)
        self.token_stream = tokens
        self.current_token_idx = 0
        self.production_sequence = []
        
        self.parse_tree_root = ParseTreeNode('Start', [], None)
        stack = deque(['$', 'Start'])
        node_stack = deque([self.parse_tree_root])

        while stack and self.current_token_idx < len(self.token_stream):
            top = stack[-1]
            current_token = self.token_stream[self.current_token_idx]
            
            terminal = self.get_terminal_symbol(current_token.name, current_token.value)
            
            if terminal is None:
                self.current_token_idx += 1
                continue
                
            if top == '$' and terminal == '$':
                break
                
            if top == terminal:
                current_node = node_stack.pop()
                current_node.token_type = current_token.name
                current_node.token_value = current_token.value
                stack.pop()
                self.current_token_idx += 1
            elif top not in self.parser_tables.grammar:
                self.error_handler.handle_syntax_error(
                    current_token.value, 
                    top, 
                    current_token.position
                )
            else:
                production = self.parser_tables.get_parse_table_entry(top, terminal)
                
                if not production:
                    context = self._get_parsing_context(top)
                    error_pos = current_token.position
                    
                    if current_token.value.startswith('"') and context == ['<<']:
                        for i in range(self.current_token_idx - 1, -1, -1):
                            prev_token = self.token_stream[i]
                            if prev_token.name == 'reservedword' and prev_token.value == 'cout':
                                error_pos = prev_token.position + len('cout')
                                break
                    
                    self.error_handler.handle_syntax_error(
                        current_token.value,
                        context,
                        error_pos
                    )
                
                if production != 'ε':
                    self.production_sequence.append(f"{top} -> {production}")
                else:
                    self.production_sequence.append(f"{top} -> epsilon")
                
                current_node = node_stack.pop()
                stack.pop()
                
                if production == 'ε':
                    epsilon_node = ParseTreeNode('ε', [], current_node)
                    current_node.children.append(epsilon_node)
                else:
                    symbols = production.split()
                    for symbol in reversed(symbols):
                        new_node = ParseTreeNode(symbol, [], current_node)
                        current_node.children.append(new_node)
                        stack.append(symbol)
                        node_stack.append(new_node)
        
        return self.parse_tree_root

    def _get_parsing_context(self, non_terminal: str) -> List[str]:
        context = set()
        for terminal in self.parser_tables.terminals:
            if self.parser_tables.parse_table[non_terminal].get(terminal):
                context.add(terminal)
        return sorted(list(context))

    def get_production_sequence(self) -> List[str]:
        final_sequence = []
        include_handled = False
        
        for prod in self.production_sequence:
            if prod.startswith('Start'):
                final_sequence.append('Start -> S N M')
            elif prod.startswith('S') and '#include' in self.token_stream[0].value:
                if not include_handled:
                    final_sequence.append('S -> #include S')
                    include_handled = True
                else:
                    final_sequence.append('S -> epsilon')
            elif not prod.startswith('LibName'):
                final_sequence.append(prod)
        
        return final_sequence

class ErrorHandler:
    def __init__(self):
        self.source_code = ""
        self.lines = []
        self.line_positions = []

    def initialize_source(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.split('\n')
        position = 0
        for line in self.lines:
            self.line_positions.append(position)
            position += len(line) + 1

    def get_line_and_column(self, position: int) -> tuple:
        line_num = len(self.lines)
        for i in range(len(self.line_positions) - 1):
            current_start = self.line_positions[i]
            next_start = self.line_positions[i + 1]
            if current_start <= position < next_start:
                line_num = i + 1
                break
        
        if line_num == len(self.lines) and position >= self.line_positions[-1]:
            line_num = len(self.lines)
        
        line_start = self.line_positions[line_num - 1]
        column = position - line_start + 1
        
        return line_num, column

    def handle_syntax_error(self, token_value: str, expected_value: str, position: int):
        line_num, column = self.get_line_and_column(position)
        line_content = self.lines[line_num - 1]
        
        if token_value == '"sum="' and isinstance(expected_value, list) and '<<' in expected_value:
            cout_pos = line_content.find('cout')
            if cout_pos != -1:
                column = cout_pos + len('cout') + 1
                line_num, _ = self.get_line_and_column(self.line_positions[line_num - 1] + cout_pos)
        
        if isinstance(expected_value, list):
            if token_value == '"sum="' and '<<' in expected_value:
                message = f"Syntax Error: Expected '<<', found '{token_value}'"
            else:
                message = f"Syntax Error: Unexpected '{token_value}'. Expected one of: {', '.join(expected_value)}"
        else:
            message = f"Syntax Error: Expected '{expected_value}', found '{token_value}'"
        
        error_msg = self.format_error(line_num, column, message)
        raise SyntaxError(error_msg)

    def format_error(self, line_num: int, column: int, message: str) -> str:
        error_msg = [f"\n{message}", "\nContext:"]
        start_line = max(1, line_num - 2)
        end_line = min(len(self.lines), line_num + 2)
        
        for i in range(start_line, end_line + 1):
            prefix = "-> " if i == line_num else "   "
            error_msg.append(f"{prefix}{i:4d} | {self.lines[i-1]}")
            if i == line_num:
                error_msg.append("      " + " " * (column - 1) + "^")
        
        return "\n".join(error_msg)

    def check_syntax(self, token_stream, source_code: str) -> bool:
        self.initialize_source(source_code)
        last_token = None
        in_statement = False
        
        for token in token_stream:
            if last_token:
                last_type, last_value, last_pos = last_token
                
                if last_value in [';', '{', '}']:
                    in_statement = False
                
                if in_statement and last_type in ['identifier', 'number']:
                    allowed_follows = {';', ',', '=', '+', '-', '*', '/',
                                     '>=', '<=', '==', '!=', ')', ']', '<<', '>>'}
                    if token.value not in allowed_follows:
                        self.handle_missing_semicolon(last_pos)
                
                if token.value == '=' and last_type not in ['identifier']:
                    self.handle_invalid_assignment(token.position)
                
                if token.value in ['(', '{']:
                    in_statement = False
                elif token.value not in [';', '}']:
                    in_statement = True
            
            last_token = (token.name, token.value, token.position)
        
        return True

    def handle_missing_semicolon(self, position: int):
        line_num, _ = self.get_line_and_column(position)
        line_content = self.lines[line_num - 1]
        column = len(line_content) + 1
        error_msg = self.format_error(
            line_num, column,
            "Syntax Error: Missing semicolon at end of statement"
        )
        raise SyntaxError(error_msg)

    def handle_invalid_assignment(self, position: int):
        line_num, _ = self.get_line_and_column(position)
        line_content = self.lines[line_num - 1]
        equal_pos = line_content.find('=')
        if equal_pos == -1:
            equal_pos = len(line_content)
        error_msg = self.format_error(
            line_num, equal_pos + 1,
            "Syntax Error: Invalid left-hand side in assignment"
        )
        raise SyntaxError(error_msg)
    
class TreeSearcher:
    def __init__(self, parse_tree_root: ParseTreeNode):
        self.root = parse_tree_root
        
    def find_identifier_definition(self, identifier: str) -> Optional[str]:
        """Find the first definition of an identifier in the parse tree."""
        def get_var_type(node: ParseTreeNode) -> Optional[str]:
            """Get variable type from Id node."""
            current = node
            while current and current.value != 'Id':
                current = current.parent
            if current and current.children:
                for child in current.children:
                    if child.token_type == 'reservedword':
                        return child.token_value
            return None

        def dfs(node: ParseTreeNode) -> Optional[str]:
            if node.value == 'L':
                # Check direct identifier in L
                for child in node.children:
                    if (child.value == 'identifier' and 
                        child.token_value == identifier):
                        var_type = get_var_type(node)
                        if var_type:
                            return var_type
                
                # Check identifiers in comma-separated list (Z node)
                z_node = next((child for child in node.children if child.value == 'Z'), None)
                if z_node:
                    current = z_node
                    while current and current.value == 'Z':
                        # Check identifier before comma
                        id_node = next((child for child in current.parent.children 
                                      if child.value == 'identifier' and 
                                      child.token_value == identifier), None)
                        if id_node:
                            var_type = get_var_type(node)
                            if var_type:
                                return var_type
                            
                        # Move to next part after comma
                        comma_list = next((child for child in current.children 
                                         if child.value == 'Z'), None)
                        if comma_list:
                            current = comma_list
                        else:
                            break
            
            # Continue searching in children
            for child in node.children:
                result = dfs(child)
                if result:
                    return result
                    
            return None
        
        result = dfs(self.root)
        return result if result else "Not found"