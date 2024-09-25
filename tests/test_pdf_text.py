import sys
import os
"""
source ~/venvML/bin/activate
"""
from pdfminer.high_level import extract_text

sys.path.append("../")
from pyCruncher.AgentOpenAI import AgentOpenAI

def test( bStream=False,  pdf_name = "/home/prokop/Desktop/ChemPhysChem - 2024 - Lamanec - Similarities and Differences of Hydridic and Protonic Hydrogen Bonding.pdf"):
   

    prompt = """
    Please sumarize this research article. The text was extracted from .pdf therefore it may contain some junk which may be ignored.
    First identify sections like: Title, Abstract, Introduction, Results, Discussion, Conclusions
    Then extract the main message, motivation, goals and results (what was achieved).
    Categorize the article into multiple narrow domains. Try to be very specific. All articles are probably form domain of physis and chemistry, that is not specific enough.
    Rather choose narrow topics, e.g. hydrogen bonding, local basiset, quaternions, post-Hatree-Fock methods, density functional theory, Graphene, DNA origami etc.
    If article contains any key formula rewrite them in latex.
    Sumay write in following format:
        1. Title
        2. Keywords (very specific research domains)
        4. essence (Main message)
        3. Motivation (Goals) 
        4. Results (What was achieved)
        5. key equations in latex
    """

    pdf_txt = extract_text(pdf_name)
    #print(pdf_txt)
    #exit()

    #agent = AgentOpenAI("groq-llama-70b")
    agent = AgentOpenAI("lm-llama-3.1")


    #print("Available models:", agent.client.models.list())
    print("user:  "+prompt+"\n\n")
    taks = prompt + pdf_txt
    with open("pdf_in.md", "w") as f: f.write(taks)
    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream(taks): print(chunk, flush=True, end="")
        result = agent.assistant_message
    else:
        result = agent.query(prompt)
        print(result)
    with open("pdf_out.md", "w") as f: f.write(result)

if __name__ == "__main__":
    test( bStream = True )