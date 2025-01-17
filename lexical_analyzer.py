import re
from typing import List
from dataclasses import dataclass

@dataclass
class Token:
    name: str
    value: str

    def __repr__(self):
        return f"[{self.name}, {self.value}]"

class LexicalAnalyzer:
    def __init__(self):
        self.patterns = [
            ('reservedword', r'#include|int|float|void|return|if|while|cin|cout|continue|break|using|iostream|namespace|std|main'),
            ('identifier', r'[a-zA-Z][a-zA-Z0-9]*'),
            ('number', r'\d+'),
            ('string', r'"[^"]*"'),
            # fix the orders becausee of miss undrestanding between < and << or > and >>
            ('symbol', r'<<|>>|<=|>=|==|!=|\(|\)|\[|\]|,|;|\+|-|\*|/|=|\|\||{|}|<|>'),
            ('whitespace', r'[ \t\n]+')
        ]
        
        # Compile patterns
        self.token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.patterns)
        self.regex = re.compile(self.token_regex)

    def tokenize(self, code: str) -> List[Token]:
        tokens = []
        position = 0

        while position < len(code):
            match = self.regex.match(code, position)
            if match is None:
                raise ValueError(f"Invalid token at position {position}")

            position = match.end()
            token_type = match.lastgroup
            token_value = match.group()

            if token_type != 'whitespace':
                if token_type == 'string':
                    # Keep the quotes in the token value
                    tokens.append(Token('string', token_value))
                else:
                    tokens.append(Token(token_type, token_value))

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
                        cout<<"sum="<<s;
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