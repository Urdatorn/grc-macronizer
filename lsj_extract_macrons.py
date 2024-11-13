import xml.etree.ElementTree as ET
import csv
from macrons_map import macrons_map

# Load the XML file
tree = ET.parse('lsj/LSJ_ENTRIES_WITH_MACRONS.XML')
root = tree.getroot()

# Open the CSV file for writing
with open('output.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    itype_count = 0  # Counter for itype elements

    # Iterate through all div2 elements
    for div2 in root.findall('.//div2'):
        head = div2.find('head')
        if head is not None:
            head_text = head.text
            orth_orig = head.get('orth_orig', '')
            print(f"Processing head: {head_text}, orth_orig: {orth_orig}")  # Debug statement
            
            # Check if orth_orig or itype contains any character from macrons_map
            if any(char in orth_orig for char in macrons_map.keys()):
                print(f"Found macron in orth_orig: {orth_orig}")  # Debug statement
                csvwriter.writerow([orth_orig])
            else:
                itype = div2.find('itype')
                if itype is not None:
                    itype_text = itype.text
                    if any(char in itype_text for char in macrons_map.keys()):
                        itype_count += 1
                        print(f"Found macron in itype for head: {head_text}, itype: {itype_text}")  # Debug statement
                        csvwriter.writerow([head_text, itype_text])

print(f"Processing complete. Total itype elements processed: {itype_count}")