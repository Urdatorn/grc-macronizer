import json
import unicodedata
from macrons_map import macrons_map

def is_conjugation_table(table):
    """Determine if the table is a conjugation table."""
    for row in table['rows']:
        if any(isinstance(cell, str) and 'active' in cell.lower() for cell in row):
            print(row, 'is in a conjugation table')
            return True
    return False


def no_macrons(form):
    """Remove macrons from a form."""
    for with_macron, without_macron in macrons_map.items():
        form = form.replace(with_macron, without_macron)
    return form

print(no_macrons("ἐπιβᾰ́λλει"))  # Output: "ἐπιβάλλει"

    
def row_header(wiktionary, form):
    "Return voice or mood of the form."
    form = no_macrons(form).strip()  # Apply no_macrons and strip whitespace
    for lemma, tables in wiktionary.items():
        for table in tables:
            for row in table["rows"]:
                # Apply no_macrons and strip whitespace for each cell in the row
                modified_row = [no_macrons(cell).strip() for cell in row]
                if form in modified_row:
                    return modified_row[0]  # Return the first entry (row header)
    return None  # Return None if the form is not found


# Import JSON data outside the function
with open('snippet.json', 'r', encoding='utf-8') as file:
    data = json.load(file)


    # Example usage
    form = "ἐπιβᾰ́λλω"
    result = row_header(data, form)
    print(form, result)  # Output: "active"

    form = "ἐπιβάλλω"
    result = row_header(data, form)
    print(form, result)  # Output: "active"

    form = "ἡ ψαλίς hē psalís"
    result = row_header(data, form)
    print(form, result)  # Output: "nominative"