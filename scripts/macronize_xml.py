import glob
from tqdm import tqdm
import xml.etree.ElementTree as ET

from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables, macronization_stats

macronizer = Macronizer(make_prints=True)

def extract_text_from_tei(xml_path):
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    tree = ET.parse(xml_path)
    root = tree.getroot()

    body = root.find('.//tei:text/tei:body', ns)
    if body is None:
        return ""

    paragraphs = []
    for p in body.findall('.//tei:p', ns):
        # Check if <p> contains a <label type="head">
        head_label = p.find('tei:label[@type="head"]', ns)
        if head_label is not None:
            continue  # skip this <p>

        # Collect all text within this <p>, including children
        text = ''.join(p.itertext()).strip()
        if text:
            paragraphs.append(text)

    for l in body.findall('.//tei:l', ns):
        # Collect all text within this <l>, including children
        text = ''.join(l.itertext()).strip()
        if text:
            paragraphs.append(text)

    return ' '.join(paragraphs)

folder_path = "/Users/albin/Downloads/xmls_for_stats"

xml_files = sorted(glob.glob(f"{folder_path}/*.xml"))
length = len(xml_files)
skipped = 0
numerator = 0
denominator = 0 

for xml_path in tqdm(xml_files, desc="Processing XML files", unit="file", total=length):
    input = extract_text_from_tei(xml_path)

    if not input:
        skipped += 1
        print(f"No text found in {xml_path}, skipping.")
        continue
    output = macronizer.macronize(input)

    a, b, c = macronization_stats(input, output)
    numerator += a
    denominator += b

    print(colour_dichrona_in_open_syllables(output[:10]))

print(skipped, "files skipped due to no text found.")

print(f"--------------------------------")
print(f"---------- Stats ---------------")
print(f"--------------------------------")

print(f"Total macronization = {numerator}/{denominator} = {numerator/denominator:.2%}")