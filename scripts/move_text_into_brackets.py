import re

def move_text_into_brackets(line):
    """
    Move text that appears between bracket pairs into the bracket to the left.
    Also moves any text after the last bracket pair into that bracket.
    
    Args:
        line (str): Input line with brackets [] and {}
        
    Returns:
        str: Modified line with text moved into brackets
    """
    # First, handle text between bracket pairs
    # Pattern to match:
    # 1. A closing bracket (] or })
    # 2. Followed by text that's not inside any brackets
    # 3. Followed by an opening bracket ([ or {)
    pattern = r'([\]\}])([^\[\]\{\}]+)([\[\{])'
    
    def replace_match(match):
        closing_bracket = match.group(1)
        text_between = match.group(2)
        opening_bracket = match.group(3)
        
        # Remove the closing bracket, add text, then add closing bracket back
        # Then add the opening bracket
        return closing_bracket[:-1] + text_between + closing_bracket[-1] + opening_bracket
    
    # Keep applying the pattern until no more matches are found
    prev_line = ""
    while prev_line != line:
        prev_line = line
        line = re.sub(pattern, replace_match, line)
    
    # Now handle any text after the last bracket pair
    # Pattern to match: closing bracket followed by text at end of line
    end_pattern = r'([\]\}])([^\[\]\{\}]+)$'
    
    def replace_end_match(match):
        bracket_content = match.group(1)
        trailing_text = match.group(2)
        
        # Remove the closing bracket, add trailing text, then add closing bracket back
        return bracket_content[:-1] + trailing_text + bracket_content[-1]
    
    line = re.sub(end_pattern, replace_end_match, line)
    
    return line

if __name__ == "__main__":
    test_line = "{Φέ}{ρ' ἴ^}[δω], {τί^} [δ' ἥσ][θη][ν ἄξ]{ι^}[ον] [χαι][ρη]{δό}[νος];"
    result = move_text_into_brackets(test_line)
    print(f"Original: {test_line}")
    print(f"Result:   {result}")
