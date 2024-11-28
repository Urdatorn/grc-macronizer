import json
import unicodedata

def is_conjugation_table(table):
    """Determine if the table is a conjugation table."""
    for row in table['rows']:
        if any(isinstance(cell, str) and 'active' in cell.lower() for cell in row):
            print(row, 'is in a conjugation table')
            return True
    return False


def row_header(data, form):
    for key, tables in data.items():
        for table in tables:
            for row in table["rows"]:
                if form in row:
                    return row[0]  # Return the first entry (row header)
    return None  # Return None if the form is not found

# Import JSON data outside the function
with open('snippet.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Example usage
form = "ἐπιβᾰ́λλει"
result = row_header(data, form)
print(result)  # Output: "active"

form = "ψᾰλῐ́ς"
result = row_header(data, form)
print(result)  # Output: "active"