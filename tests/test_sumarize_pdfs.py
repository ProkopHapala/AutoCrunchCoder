import os
import sys
from pdfminer.high_level import extract_text

sys.path.append("../")
from pyCruncher.AgentOpenAI import AgentOpenAI
from pyCruncher.file_utils  import find_and_process_files, write_file, read_file

# Helper function to process a single PDF file
def process_pdf(pdf_path, output_dir, pdf_num):
    output_name = f"PDF_{pdf_num:05d}"
    output_file = os.path.join(output_dir, output_name + ".md")
    pdf_text    = extract_text(pdf_path)                  # Extract text from PDF
    nchar       = len(pdf_text)                           # get lenght
    log = f"{output_name} {nchar:<7} {pdf_path}\n"
    print(log,)
    write_file(output_dir+"pdf_to_md.log", log , mode="a")
    write_file(output_file, pdf_text)                     # Save extracted text to .md file
    #logging.info(f"{output_name}, {nchar}, {pdf_path}")   # Log file details
    return output_name, nchar

# Function to process all PDFs in a given directory
def process_all_pdfs( input_dir, output_dir, pdf_files=None):
    if pdf_files is None:
        pdf_files = find_and_process_files(input_dir, relevant_extensions={'.pdf'})
    pdf_num = 1
    #write_file(output_dir,  "", mode="w")
    for pdf_file in pdf_files:
        process_pdf(pdf_file, output_dir, pdf_num)
        pdf_num += 1

def article_to_llm( agent, fname, input_dir="./", output_dir="./", bStream=False, ncharmax = 300000 ):
    #print("Available models:", agent.client.models.list())
    #print("agent: "+"\n\n")
    txt = read_file( input_dir+fname )
    task = prompt + pdf_txt
    nchar = len(task)
    if nchar >= ncharmax:
        log = f"{fname} too long: nchar={nchar} > ncharmax={pdf_path}\n"
        print(log,)
        write_file( output_dir+"md_files_to_llm.log", log, mode="a")
        return
    if bStream:
        for chunk in agent.stream(task): print(chunk, flush=True, end="")
        result = agent.assistant_message
    else:
        result = agent.query(prompt)
    write_file( output_dir+fname, result )

# Function to process .md files and send them to LLM
def md_files_to_llm(input_dir, output_dir, md_files=None ):
    if md_files is None:
        md_files = find_and_process_files(input_dir, relevant_extensions={'.md'})   # Find all .md files in output directory
    agent=AgentOpenAI("fzu-llama-8b")
    for fname in md_files:
        print( fname )
        article_to_llm( agent, fname=fname, input_dir=input_dir, output_dir=output_dir )

# Main entry point for the script
if __name__ == '__main__':
    input_dir  = '/home/prokophapala/Desktop/PAPERs/'  
    output_dir   = '/home/prokophapala/Desktop/PAPERs_meta/'
    output_dir_1 = '/home/prokophapala/Desktop/PAPERs_meta/extracted_fulltext/'  
    output_dir_2 = '/home/prokophapala/Desktop/PAPERs_meta/summary/'
    #if not os.path.exists(output_dir):    os.makedirs(output_dir)
    
    pdf_files = find_and_process_files(input_dir, relevant_extensions={'.pdf'})
    #for pdf_file in pdf_files: print(pdf_file)
    process_all_pdfs( input_dir, output_dir_1, pdf_files=pdf_files)

    #md_files = find_and_process_files(input_dir, relevant_extensions={'.md'})   # Find all .md files in output directory
    #for fname in md_files: print(fname)
    #process_md_files(output_dir_1,output_dir_2, md_files=md_files )
