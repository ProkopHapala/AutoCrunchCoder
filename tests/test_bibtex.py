

import sys
sys.path.append('../python')
import bib_utils as bu
import LMagent 

from pdfminer.high_level import extract_text

# Example usage (replace 'entries' with actual BibTeX content split into entries):
# with open('/home/prokop/Mendeley Desktop/library.bib', 'r') as file:
#     bibtex_content = file.read()

# entries = bibtex_content.split('@')
# results = bu.process_bibtex_entries(entries)

#print( results )

# Print results
#print("Top 20 Bigrams:", results['bigrams'])
#print("Top 20 Trigrams:", results['trigrams'])
#print("Top 50 Keywords:", results['keywords'])

#for keyw,num in results['keywords']: print(keyw,num)

system_prompt="""
Sumarize following text extracted from .pdf of a research article. 
Your output should extract the key insights from the article. And it should define 10 keywords resp. research areas where to classify the article.
Notice that there can be words, numbers and special symbols out-of-place since the equations, tables, figure description and other formats can be broken during the pdf-to-text conversion.
"""

#model_name="QuantFactory/deepseek-math-7b-instruct-GGUF/deepseek-math-7b-instruct.Q4_0.gguf"
#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
#model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
model_name="lmstudio-community/Phi-3.1-mini-128k-instruct-GGUF/Phi-3.1-mini-128k-instruct-Q4_K_M.gguf"


llm = LMagent.Agent(model_name=model_name)
llm.set_system_prompt( system_prompt )


def sumarize_pdf( fname, max_len=1024 ):
    #extract_text( fname, output_dir='./' )
    text = extract_text(fname)
    respose = llm.send_message( text[:max_len] ); 
    print("LLM: " + respose)


bu.load_bib( fname='/home/prokop/Mendeley Desktop/library.bib', file_func=sumarize_pdf )