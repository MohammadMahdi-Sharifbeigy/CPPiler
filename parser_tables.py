from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import hashlib

@dataclass
class TokenTableEntry:
    token_name: str
    token_value: str
    hash_value: str

class ParserTables:
    def __init__(self):
        self.token_table: List[TokenTableEntry] = []
        self.parse_table: Dict[str, Dict[str, str]] = {}
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        
        # Map token types to their terminal symbols
        self.token_to_terminal = {
            ('reservedword', '#include'): '#include',
            ('reservedword', 'using'): 'using',
            ('reservedword', 'namespace'): 'namespace',
            ('reservedword', 'std'): 'std',
            ('reservedword', 'int'): 'int',
            ('reservedword', 'float'): 'float',
            ('reservedword', 'main'): 'main',
            ('reservedword', 'while'): 'while',
            ('reservedword', 'cin'): 'cin',
            ('reservedword', 'cout'): 'cout',
            ('reservedword', 'return'): 'return',
            ('symbol', '{'): '{',
            ('symbol', '}'): '}',
            ('symbol', '('): '(',
            ('symbol', ')'): ')',
            ('symbol', ';'): ';',
            ('symbol', ','): ',',
            ('symbol', '='): '=',
            ('symbol', '+'): '+',
            ('symbol', '-'): '-',
            ('symbol', '*'): '*',
            ('symbol', '>='): '>=',
            ('symbol', '<='): '<=',
            ('symbol', '=='): '==',
            ('symbol', '!='): '!=',
            ('symbol', '>>'): '>>',
            ('symbol', '<<'): '<<',
            ('identifier', None): 'identifier',
            ('number', None): 'number',
            ('string', None): 'string'
        }
        
        self.terminals = {v for v in self.token_to_terminal.values()} | {'$'}
        
        self.non_terminals = {
            'Start', 'S', 'N', 'M', 'T', 'V', 'Id', 'L', 'Z', 'Operation',
            'P', 'O', 'W', 'Assign', 'Expression', 'K', 'Loop', 'Input',
            'F', 'Output', 'H', 'C'
        }
        
        self.grammar = {
            'Start': ['S N M'],
            'S': ['#include S', 'ε'],
            'N': ['using namespace std ;', 'ε'],
            'M': ['int main ( ) { T V }'],
            'T': ['Id T', 'L T', 'Loop T', 'Input T', 'Output T', 'ε'],
            'V': ['return 0 ;', 'ε'],
            'Id': ['int L', 'float L'],
            'L': ['identifier Assign Z'],
            'Z': [', identifier Assign Z', ';'],
            'Operation': ['number P', 'identifier P'],
            'P': ['O W P', 'ε'],
            'O': ['+', '-', '*'],
            'W': ['number', 'identifier'],
            'Assign': ['= Operation', 'ε'],
            'Expression': ['Operation K Operation'],
            'K': ['==', '>=', '<=', '!='],
            'Loop': ['while ( Expression ) { T }'],
            'Input': ['cin >> identifier F ;'],
            'F': ['>> identifier F', 'ε'],
            'Output': ['cout << C H ;'],
            'H': ['<< C H', 'ε'],
            'C': ['number', 'string', 'identifier']
        }

    def compute_hash(self, token_value: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(token_value.encode('utf-8'))
        return hasher.hexdigest()[:8]

    def get_terminal(self, token_type: str, token_value: str) -> str:
        """Convert token to terminal symbol."""
        if token_type == 'symbol':
            if token_value == '#':
                return '#include'
                
            if token_value in ['<<', '>>']: # Input/output operators
                return token_value
                
            if token_value in ['<=', '>=', '==', '!=']:  # Comparison operators
                return token_value
                
            return token_value
            
        if token_type == 'reservedword':
            return token_value
            
        if token_type in ['identifier', 'number', 'string']:
            return token_type
            
        return token_value

    def add_token(self, token_name: str, token_value: str):
        hash_value = self.compute_hash(token_value)
        entry = TokenTableEntry(token_name, token_value, hash_value)
        
        token_order = {
            'string': 0,
            'number': 1,
            'symbol': 2,
            'identifier': 3,
            'reservedword': 4
        }
        
        insert_pos = 0
        for i, existing in enumerate(self.token_table):
            if token_order[existing.token_name] > token_order[token_name]:
                break
            if (token_order[existing.token_name] == token_order[token_name] and 
                existing.token_value > token_value):
                break
            insert_pos = i + 1
            
        self.token_table.insert(insert_pos, entry)

    def _is_terminal(self, symbol: str) -> bool:
        """Check if a symbol is a terminal."""
        return symbol in self.terminals or symbol == 'ε'

    def compute_first_sets(self):
        """Compute FIRST sets for all non-terminals."""
        self.first_sets = {nt: set() for nt in self.non_terminals}
        
        changed = True
        while changed:
            changed = False
            for nt, productions in self.grammar.items():
                for prod in productions:
                    symbols = prod.split()
                    
                    if not symbols or symbols[0] == 'ε':
                        if 'ε' not in self.first_sets[nt]:
                            self.first_sets[nt].add('ε')
                            changed = True
                        continue
                    
                    all_nullable = True
                    for symbol in symbols:
                        if self._is_terminal(symbol):
                            if symbol not in self.first_sets[nt]:
                                self.first_sets[nt].add(symbol)
                                changed = True
                            all_nullable = False
                            break
                        else:  # Non-terminal
                            for s in self.first_sets[symbol] - {'ε'}:
                                if s not in self.first_sets[nt]:
                                    self.first_sets[nt].add(s)
                                    changed = True
                            if 'ε' not in self.first_sets[symbol]:
                                all_nullable = False
                                break
                                
                    if all_nullable and 'ε' not in self.first_sets[nt]:
                        self.first_sets[nt].add('ε')
                        changed = True

    def compute_follow_sets(self):
        """Compute FOLLOW sets for all non-terminals."""
        self.follow_sets = {nt: set() for nt in self.non_terminals}
        self.follow_sets['Start'].add('$')
        
        changed = True
        while changed:
            changed = False
            for nt, productions in self.grammar.items():
                for prod in productions:
                    symbols = prod.split()
                    
                    for i, symbol in enumerate(symbols):
                        if symbol not in self.non_terminals:
                            continue
                            
                        trailer = symbols[i + 1:]
                        first_of_trailer = self._compute_first_of_string(trailer)
                        
                        for terminal in first_of_trailer - {'ε'}:
                            if terminal not in self.follow_sets[symbol]:
                                self.follow_sets[symbol].add(terminal)
                                changed = True
                                
                        if 'ε' in first_of_trailer:
                            for terminal in self.follow_sets[nt]:
                                if terminal not in self.follow_sets[symbol]:
                                    self.follow_sets[symbol].add(terminal)
                                    changed = True

    def _compute_first_of_string(self, symbols: List[str]) -> Set[str]:
        if not symbols:
            return {'ε'}
            
        result = set()
        all_nullable = True
        
        for symbol in symbols:
            if self._is_terminal(symbol):
                result.add(symbol)
                all_nullable = False
                break
            else:
                result.update(self.first_sets[symbol] - {'ε'})
                if 'ε' not in self.first_sets[symbol]:
                    all_nullable = False
                    break
                    
        if all_nullable:
            result.add('ε')
            
        return result

    def build_parse_table(self):
        """Build the predictive parsing table."""
        self.compute_first_sets()
        self.compute_follow_sets()
        
        self.parse_table = {
            nt: {t: '' for t in self.terminals} 
            for nt in self.non_terminals
        }
        
        for nt, productions in self.grammar.items():
            for prod in productions:
                first_of_prod = self._compute_first_of_string(prod.split())
                
                for terminal in first_of_prod - {'ε'}:
                    if self.parse_table[nt][terminal]:
                        raise ValueError(
                            f"Grammar is not LL(1): Conflict at {nt}, {terminal}"
                        )
                    self.parse_table[nt][terminal] = prod
                
                if 'ε' in first_of_prod:
                    for terminal in self.follow_sets[nt]:
                        if self.parse_table[nt][terminal]:
                            raise ValueError(
                                f"Grammar is not LL(1): Conflict at {nt}, {terminal}"
                            )
                        self.parse_table[nt][terminal] = 'ε'

    def get_parse_table_entry(self, non_terminal: str, terminal: str) -> str:
        """Get the production rule for a given non-terminal and terminal."""
        if non_terminal not in self.parse_table:
            raise ValueError(f"Unknown non-terminal: {non_terminal}")
        if terminal not in self.parse_table[non_terminal]:
            raise ValueError(f"Unknown terminal: {terminal}")
        return self.parse_table[non_terminal][terminal]