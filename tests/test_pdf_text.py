import os
import sys
sys.path.append("../")
"""
pip install pdfminer.six
source ~/venvML/bin/activate
"""
from pdfminer.high_level import extract_text
from pyCruncher.AgentOpenAI import AgentOpenAI

prompt = """
Please summarize the following research article.  
The text was extracted from a PDF and may contain irrelevant characters or formatting errors, which can be ignored.

### Instructions:

1. **Section Identification**: Identify and segment the following sections, if present:
   - Title
   - Abstract
   - Introduction
   - Results
   - Discussion
   - Conclusions

2. **Core Extraction**:
   - Extract the **main message** of the paper.
   - Identify the **motivation** and **goals** of the research.
   - Highlight the **results** and what was achieved.

3. **Categorization**:
   - Classify the article into **narrow, specific domains**. Avoid broad categories like "physics" or "chemistry." 
   - Instead, use precise topics such as "hydrogen bonding," "local basis sets," "quaternions," "post-Hartree-Fock methods," "density functional theory," "graphene," "DNA origami," etc.

4. **Formulas, Methods, and Abbreviations**:
   - If the article contains any key equations, rewrite them in LaTeX.
   - List any computational or experimental methods, as well as abbreviations mentioned, such as B3LYP, pVDZ, FFT, AFM, DFT, etc.

5. **Format**: Present the summary in the following structure:
   1. **Title**
   2. **Keywords** (specific research domains)
   3. **Essence** (Main message)
   4. **Motivation** (Goals)
   5. **Results** (What was achieved)
   6. **Key Equations** (in LaTeX, if applicable)
   7. **Methods and Abbreviations**

**Conciseness and Focus**:
   - Keep the summary concise and structured, with a maximum length of one A4 page.
   - Focus on the **main findings**, avoiding excessive details or filler text.

The raw text extracted from the article follows below:  
----------------------
"""

def test( bStream=False,  pdf_name = None, ncharmax = 300000 ):
    
    if pdf_name is None:
        pdf_name = "/home/prokophapala/Desktop/PAPERs/Elner_triazine_PhysRevB.96.075418.pdf"

    pdf_txt = extract_text(pdf_name)
    #print(pdf_txt)
    #print("user:  "+prompt+"\n\n")
    print(pdf_name)
    
    task = prompt + pdf_txt
    nchar = len(task)

    with open("pdf_in.md", "w") as f: f.write(task)
    print( "char_count: ", nchar )
    if nchar >= ncharmax:
        print( "char_count: ", nchar, " >= ", ncharmax )
        exit()

    #agent = AgentOpenAI("groq-llama-70b")
    #agent = AgentOpenAI("lm-llama-8b")
    agent = AgentOpenAI("fzu-llama-8b")
    #print("Available models:", agent.client.models.list())

    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream(task): print(chunk, flush=True, end="")
        result = agent.assistant_message
    else:
        result = agent.query(prompt)
        print(result)
    with open("pdf_out.md", "w") as f: f.write(result)

if __name__ == "__main__":
    test( bStream = True )