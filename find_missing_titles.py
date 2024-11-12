import os

def find_missing_titles(titles_file, html_folder, output_file="missing_titles.txt"):
    # Read all titles from titles_file
    with open(titles_file, "r", encoding="utf-8") as f:
        titles = {line.strip() for line in f.readlines()}

    # Get all HTML filenames without the .html extension in the html_folder
    html_files = {os.path.splitext(filename)[0] for filename in os.listdir(html_folder) if filename.endswith(".html")}

    # Find titles that are missing in the html_folder
    missing_titles = titles - html_files

    # Output the missing titles to a file
    with open(output_file, "w", encoding="utf-8") as f:
        for title in sorted(missing_titles):
            f.write(f"{title}\n")

    print(f"Missing titles have been written to {output_file}")

# Specify paths
titles_file = "wiktionary_titles.txt"
html_folder = "wiktionary_htmls"

# Run the function
find_missing_titles(titles_file, html_folder)