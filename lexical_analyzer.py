import re
from typing import List
from dataclasses import dataclass

@dataclass
class Token:
    name: str
    value: str
    position: int = 0
    line: int = 1
    column: int = 1

    def __repr__(self):
        return f"[{self.name}, {self.value}, pos={self.position}, ln={self.line}, col={self.column}]"

class LexicalAnalyzer:
    def __init__(self):
        self.patterns = [
            ('reservedword', r'#include|int|float|void|return|if|while|cin|cout|continue|break|using|iostream|namespace|std|main'),
            ('identifier', r'[a-zA-Z][a-zA-Z0-9]*'),
            ('number', r'\d+'),
            ('string', r'"[^"]*"'),
            # Order matters: handle compound operators before single ones
            ('symbol', r'<<|>>|<=|>=|==|!=|\(|\)|\[|\]|,|;|\+|-|\*|/|=|\|\||{|}|<|>'),
            ('whitespace', r'[ \t\n]+')
        ]
        
        # Compile patterns
        self.token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.patterns)
        self.regex = re.compile(self.token_regex)
        
    def tokenize(self, code: str) -> List[Token]:
        tokens = []
        position = 0
        line = 1
        column = 1
        print("\nDEBUG Lexical Analysis:")
        
        while position < len(code):
            match = self.regex.match(code, position)
            if match is None:
                raise ValueError(f"Invalid token at position {position}")

            token_type = match.lastgroup
            token_value = match.group()
            token_start = position  # Save start position before updating
            
            # Handle whitespace
            if token_type == 'whitespace':
                for char in token_value:
                    if char == '\n':
                        line += 1
                        column = 1
                        position += 1
                    else:
                        column += 1
                        position += 1
                continue

            # Create token with position info
            if token_type == 'identifier' or token_type == 'reservedword':
                if token_value == 'iostream':
                    token = Token('reservedword', token_value, position, line, column)
                else:
                    token = Token(token_type, token_value, position, line, column)
                tokens.append(token)
                print(f"Token: {token}")
            else:
                token = Token(token_type, token_value, position, line, column)
                tokens.append(token)
                print(f"Token: {token}")

            # Update position and column
            position = match.end()
            column += len(token_value)

        return tokens
    
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
    cout"sum="<<s;
    return 0;
}"""

    analyzer = LexicalAnalyzer()
    try:
        tokens = analyzer.tokenize(test_code)
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

if __name__ == "__main__":
    main()