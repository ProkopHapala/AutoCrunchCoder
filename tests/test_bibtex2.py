import bibtexparser

# Load the BibTeX file
with open('/home/prokop/Mendeley Desktop/library.bib', 'r') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

# Access the entries
entries = bib_database.entries

# Example: Print titles of all entries
for entry in entries:
    print(entry.get('title'))

# Example: Extract titles and abstracts
titles_and_abstracts = [(entry.get('title'), entry.get('abstract', '')) for entry in entries]

# Example: Modify an entry
if entries:
    entries[0]['title'] = "New Title"

# Export the modified entries back to a BibTeX file
with open('/home/prokop/Mendeley Desktop/library-mod.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database, bibtex_file)
