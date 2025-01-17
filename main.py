from lexical_analyzer import LexicalAnalyzer, Token
from parser_tables import ParserTables
from predictive_parser import PredictiveParser, ErrorHandler, TreeSearcher
from tabulate import tabulate
import sys

def print_parse_table(parse_table, terminals, non_terminals):
    """Print parse table in a clear, readable format."""
    print("\n=== Parse Table ===\n")
    
    # Filter out unused terminals
    used_terminals = []
    for terminal in sorted(terminals):
        for nt in non_terminals:
            if parse_table[nt].get(terminal):
                used_terminals.append(terminal)
                break
    
    # Print productions for each non-terminal
    for nt in sorted(non_terminals):
        print(f"{nt}:")
        has_productions = False
        for terminal in used_terminals:
            production = parse_table[nt].get(terminal, '')
            if production:
                has_productions = True
                if production == 'ε':
                    production = 'epsilon'
                print(f"  {terminal:<15} -> {production}")
        if not has_productions:
            print("  <no productions>")
        print()

def print_token_table(token_table):
    """Print token table in a simple list format."""
    print("\n=== Token Table ===\n")
    
    current_type = None
    for entry in token_table:
        if entry.token_name != current_type:
            current_type = entry.token_name
            print(f"\n{current_type.upper()}:")
        print(f"  {entry.token_value:<20} (hash: {entry.hash_value})")

def print_productions(productions):
    """Print production sequence in a clear format."""
    print("\n=== Production Sequence ===\n")
    for i, prod in enumerate(productions, 1):
        print(f"{i:3}. {prod}")

def print_identifier_table(identifiers):
    """Print identifier definitions in a clear format."""
    print("\nIdentifier Definitions:")
    for identifier, definition in identifiers:
        print(f"  {identifier:<10} -> {definition}")

def main():
    test_code = """#include <iostream>
                    using namespace std;
                    int main(){
                        int x;
                        int s=0, t=10;
                        while (t >= 0){
                            cin>>x;
                            t = t - 1;
                            s = s + x;
                        }
                        cout<<"sum="<<s;
                        return 0;
                    }"""

    print("=== Testing CPPiler ===")
    print("\nInput Code:")
    print("-" * 40)
    print(test_code)
    print("-" * 40)

    try:
        print("\nPhase 1: Lexical Analysis")
        lexer = LexicalAnalyzer()
        
        try:
            tokens = lexer.tokenize(test_code)
            print("\nTokens:")
            tokens_iter = iter(tokens)
            while True:
                row = []
                for _ in range(3):
                    try:
                        token = next(tokens_iter)
                        row.append(f"{token}")
                    except StopIteration:
                        break
                if not row:
                    break
                while len(row) < 3:
                    row.append("")
                print(f"{row[0]:<25} {row[1]:<25} {row[2]}")
                
            print(f"\nSuccessfully tokenized {len(tokens)} tokens.")
            
        except ValueError as e:
            print(f"Lexical Error: {str(e)}")
            return

        print("\nPhase 2: Parser Tables Construction")
        parser_tables = ParserTables()
        
        current_pos = 0
        for token in tokens:
            parser_tables.add_token(token.name, token.value)
            current_pos += len(token.value) + 1 
        
        try:
            parser_tables.build_parse_table()
            
            print("\n=== Token Table ===")
            current_type = None
            for entry in parser_tables.token_table:
                if entry.token_name != current_type:
                    current_type = entry.token_name
                    print(f"\n{current_type.upper()}:")
                print(f"  {entry.token_value:<20} (hash: {entry.hash_value})")
            
            print("\n=== Parse Table ===")
            terminals = sorted(parser_tables.terminals)
            non_terminals = sorted(parser_tables.grammar.keys())
            
            for nt in non_terminals:
                print(f"\n{nt}:")
                for terminal in terminals:
                    production = parser_tables.parse_table[nt].get(terminal, '')
                    if production:
                        if production == 'ε':
                            production = 'epsilon'
                        print(f"  {terminal:<15} -> {production}")
                        
        except ValueError as e:
            print(f"Error in parse table construction: {str(e)}")
            return

        print("\nPhase 3: Parsing")
        parser = PredictiveParser(parser_tables)
        
        current_pos = 0
        token_stream = []
        for token in tokens:
            token_stream.append((token.name, token.value, current_pos))
            current_pos += len(token.value) + 1
        token_stream.append(('$', '$', current_pos))
        
        try:
            # Parse tokens and initialize error handler with source code
            parse_tree = parser.parse(token_stream, test_code)
            productions = parser.get_production_sequence()
            
            print("\n=== Production Sequence ===")
            for i, prod in enumerate(productions, 1):
                print(f"{i:3}. {prod}")
            
            print("\n=== Extra Features ===")
            
            # Tree Search
            tree_searcher = TreeSearcher(parse_tree)
            test_identifiers = ['x', 's', 't']
            print("\nIdentifier Definitions:")
            for identifier in test_identifiers:
                definition = tree_searcher.find_identifier_definition(identifier)
                if definition:
                    print(f"  {identifier:<10} -> {definition}")
                else:
                    print(f"  {identifier:<10} -> Not found")
            
            # Check syntax
            if error_handler.check_syntax(token_stream, test_code):
                print("\nSuccess! All phases completed with no syntax errors.")
            
        except SyntaxError as e:
            print(f"\nSyntax Error:\n{str(e)}")
            
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()