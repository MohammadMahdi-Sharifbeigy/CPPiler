from lexical_analyzer import LexicalAnalyzer, Token
from parser_tables import ParserTables
from predictive_parser import PredictiveParser, ErrorHandler, TreeSearcher
from tabulate import tabulate
import sys

def print_parse_table(parse_table, terminals, non_terminals):
    """Print parse table in a clear, readable format."""
    print("\n=== Parse Table ===\n")
    
    used_terminals = []
    for terminal in sorted(terminals):
        for nt in non_terminals:
            if parse_table[nt].get(terminal):
                used_terminals.append(terminal)
                break
    
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
        except ValueError as e:
            print(f"Error: {e}")
        
        tokens = lexer.tokenize(test_code)
        
        print(f"Successfully tokenized {len(tokens)} tokens.")
        
        print("\nPhase 2: Parser Tables Construction")
        parser_tables = ParserTables()
        
        for token in tokens:
            parser_tables.add_token(token.name, token.value)
        
        parser_tables.build_parse_table()
        
        print_token_table(parser_tables.token_table)
        print_parse_table(
            parser_tables.parse_table,
            parser_tables.terminals,
            parser_tables.grammar.keys()
        )
        
        print("\nPhase 3: Parsing")
        parser = PredictiveParser(parser_tables)
        error_handler = ErrorHandler()
        
        token_stream = [(t.name, t.value) for t in tokens]
        token_stream.append(('$', '$'))
        
        try:
            parse_tree = parser.parse(token_stream)
            productions = parser.get_production_sequence()
            print_productions(productions)
            
            print("\n=== Extra Features ===")
            
            tree_searcher = TreeSearcher(parse_tree)
            test_identifiers = ['x', 's', 't']
            identifiers = []
            for identifier in test_identifiers:
                definition = tree_searcher.find_identifier_definition(identifier)
                identifiers.append((identifier, definition or "Not found"))
            print_identifier_table(identifiers)
            
            print("\nSuccess! All phases completed.")
            
        except SyntaxError as e:
            print(f"\nSyntax Error: {str(e)}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()