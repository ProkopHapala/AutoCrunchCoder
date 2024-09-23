from sklearn.feature_extraction.text import CountVectorizer
import re
from collections import defaultdict, Counter
import bibtexparser
#from pdfminer.high_level import extract_text
import sys
import latexcodec

# Define common words to filter out
common_words = set([
    'and', 'the', 'of', 'in', 'for', 'with', 'on', 'at', 'to', 'from', 'by', 'as', 'is', 'or', 
    'an', 'it', 'that', 'which', 'this', 'are', 'be', 'we', 'have', 'can', 'will', 'has', 
    'but', 'not', 'our', 'their', 'these', 'those', 'there', 'any', 'more', 'all', 'one', 'two',
    'using', 'used', 'new', 'its', 'between', 'high', 'low', 'both', 'many', 'some', 'only', 'such'
])

# Add BibTeX-specific common words to filter out
additional_common_words = {
    'abstract', 'title', 'author', 'doi', 'isbn', 'issn', 'issue', 'month', 
    'pages', 'pmid', 'publisher', 'volume', 'url', 'year'
}
common_words.update(additional_common_words)

debug_count = 0

def extract_ngrams(text, n=2):
    vectorizer = CountVectorizer(ngram_range=(n, n))
    ngrams = vectorizer.fit_transform([text])

    ngram_counts = ngrams.sum(axis=0).A1
    ngram_features = vectorizer.get_feature_names_out()

    ngram_dict = dict(zip(ngram_features, ngram_counts))
    sorted_ngrams = sorted(ngram_dict.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_ngrams

def convert_custom_path(custom_path):
    # Remove the leading colon (if present)
    if custom_path.startswith(':'):
        custom_path = custom_path[1:]
    # Remove the trailing file type indicator (if present)
    if custom_path.endswith(':pdf'):
        custom_path = custom_path[:-4]
    return custom_path

def decode_latex(encoded_str):
    """Decode a LaTeX-encoded string into a regular Unicode string and clean up extra braces."""
    try:
        # Decode the LaTeX-encoded string
        decoded_str = encoded_str.encode('utf-8').decode('latex+utf-8')

        # Remove double curly braces and unnecessary braces around single characters
        cleaned_str = re.sub(r'\{\{(.+?)\}\}', r'\1', decoded_str)
        cleaned_str = re.sub(r'\{(.+?)\}', r'\1', cleaned_str)

        return cleaned_str
    except Exception as e:
        print(f"Error decoding LaTeX string: {e}")
        return encoded_str  # Return the original string if decoding fails
    
def load_bib( fname='/home/prokop/Mendeley Desktop/library.bib', file_func=None, abstract_func=None, nmax=10, fout=None ):
    if fout is None:
        # standarrd output
        fout = sys.stdout
    # Load the BibTeX file
    with open( fname, 'r') as bibtex_file:
        print( "loading bibtex file: ", fname )
        bib_database = bibtexparser.load(bibtex_file)    
    entries = bib_database.entries   # Access the entries
    # Example: Print titles of all entries
    #for entry in entries: print(entry.get('title'))

    # Example: Extract titles and abstracts
    #titles_and_abstracts = [(entry.get('title'), entry.get('abstract', '')) for entry in entries]
    i=1
    for entry in entries:
        title   = entry.get('title').strip()
        if title.startswith('{') and title.endswith('}'):title = title[1:-1]
        #title = title[0]
        author = entry.get('author')
        abstract = entry.get('abstract')
        keywords = entry.get('keywords')
        doi = entry.get('doi')
        url = entry.get('url')
        fil = entry.get('file')

        #"~/home/prokop/Mendeley Desktop/Journal of Chemical Theory and Computation/Řezáč - 2017 - Empirical Self-Consistent Correction for the Description of Hydrogen Bonds in DFTB3.pdf"
        #"~/home/prokop/Mendeley Desktop/Journal of Chemical Theory and Computation/Řezáč - 2017 - Empirical Self-Consistent Correction for the Description of Hydrogen Bonds in DFTB3.pdf"

        rec = "\nTitle: "+title+"\n\n"
        rec_id = "======== "+ str(i) + " : "+ entry.get('ID') 
        print( rec_id )
        fout.write(              "\n"+rec_id+"\n" )
        fout.write(              "\n@title:    "+ title )
        if keywords: 
            kws=str(keywords)
            fout.write( "\n@keywords: "+ kws )
            rec += "\nkeywords: "+kws+"\n"
        if author:   fout.write( "\n@author:   "+ author )
        if doi:      fout.write( "\n@doi:      "+ doi )
        if url:      fout.write( "\n@url:      "+ url )
        # if fil:      
        #     fil = fil.split(';')[0]
        #     fout.write( "\n@file:     "+ fil )
        #     #print("file ---- BEFORE :", fil )
        #     fil = convert_custom_path(fil)
        #     fil = "/" +  decode_latex(fil)
        #     #print("file ---- AFTER :", fil )
        #     if file_func is not None:
        #         file_func( fil )
        if abstract: 
            fout.write( "\n@abstract:\n "+  abstract )
            rec += "\nabstract:\n "+abstract+"\n"
            if abstract_func is not None:
                abstract_func( fout, rec )

        #print( "========\n" )
        #print( title +"\n\n")
        #print( abstract+"\n" )

        #text = extract_text(fil)



        #if abstract: print( "text:\n ",  text )

        i+=1
        if i>nmax: break

