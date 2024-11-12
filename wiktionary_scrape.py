import os
import requests
from tqdm import tqdm

# Hardcoded list of titles to download
titles = [
    "Αἰγυπτίαι", "Αἶαν", "Γαίῃ", "Γαῖαν", "Γεννήτωρ", "Γῆν", "Γῆς", "Γῇ",
    "Εἰρήνην", "Εἰρήνης", "Εἰρήνῃ", "Θάνατον", "Θανάτου", "Θανάτῳ", "Κόρος",
    "Λάβδα", "Μελάνθιον", "Μηλίᾳ", "Νυκτί", "Νυκτός", "Νύκτα", "Οὐρανόν",
    "Πανάχραντος", "Πανός", "Παράδεισος", "Παραδείσῳ", "Πατήρ", "Πλούτου",
    "Πλούτῳ", "Πλοῦτον", "Πόντον", "Πόντου", "Πόντῳ", "Τύχης", "Υἱόν",
    "Φιλόξενος", "Φοίνικι", "Φόβον", "Φόβου", "Φόβῳ", "αἰπύ", "αἰτίαι", "βίαι",
    "δήλου", "δαίδαλα", "ζεῦξις", "θήρας", "θεολογίαι", "θεοτόκε", "θεοτόκον",
    "θεοτόκου", "θινί", "καμάρᾳ", "κῆρες", "λίβανος", "λυσανίαι", "λυτέᾳ",
    "μορμώ", "νεανίᾳ", "νότος", "οἰκίᾳ", "οἰκονομίαι", "πέλωρος", "πενίαι",
    "προδοσίᾳ", "πύλαι", "σειρήν", "σοφίαι", "σωτηρίαι", "τιμωρίαι", "φίλαι",
    "φαραώ", "ἀθρόαι", "ἀμνησίαι", "ἀναισθησίαι", "ἀπιστίαι", "ἀποικίαι",
    "ἀπορίαι", "ἀρχιτεκτονίαι", "ἄκαστος", "ἄκραι", "ἄκρᾳ", "ἄτην", "Ἀνάγκην",
    "Ἀνάγκης", "Ἀνάγκῃ", "ἐκκλησίαι", "ἐκτομίαι", "ἐξουσίᾳ", "ἐπίγονος",
    "ἐρέβει", "ἐρέβεσι", "ἐρέβεσιν", "ἐρέβη", "ἐρέβους", "ἐρεβοῖν", "ἐρεβῶν",
    "ἔχθραι", "Ἐπίμαχος", "Ἔριδι", "Ἔριδος", "ἡδονήν", "ἡμέραι", "Ἠελίῳ", "Ἠοῖ",
    "Ἠοῦς", "Ἡδονῆς", "Ἡδονῇ", "Ἥβην", "Ἥβῃ", "ἰκέλου", "ἰκέλῳ", "ἰσθμοῦ",
    "ἴκελε", "ἴκελον", "Ὑβλαῖος", "Ὑμένος", "Ὕπνον", "Ὕπνου", "Ὕπνῳ"
]

# Output folder for HTML files
output_folder = "temp"
os.makedirs(output_folder, exist_ok=True)

# Download each title's page and save as HTML with a "?" suffix
for title in tqdm(titles, desc="Downloading Wiktionary pages"):
    # Add "?" to each filename
    output_path = os.path.join(output_folder, f"{title}?.html")
    url = f"https://en.wiktionary.org/wiki/{title}"
    
    try:
        # Send GET request to download the HTML content
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Check if request was successful
        
        # Save HTML to file
        with open(output_path, "w", encoding="utf-8") as html_file:
            html_file.write(response.text)
    except requests.RequestException as e:
        print(f"Failed to download {title}: {e}")