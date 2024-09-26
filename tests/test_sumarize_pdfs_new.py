import sys
import os
from pdfminer.high_level import extract_text
sys.path.append("../")
from pyCruncher.AgentOpenAI import AgentOpenAI
from pyCruncher.file_utils import find_files, load_file_paths, read_file, process_files_serial, process_files_parallel, write_file

def pdf_to_md(pdf_path, output_dir, pdf_num):
    """
    Callback for processing a single PDF file (extract text and save to .md).
    """
    output_name = f"PDF_{pdf_num:05d}"
    output_file = os.path.join(output_dir, output_name + ".md")

    if os.path.exists(output_file):
        print(f"Skipping {pdf_path} as the .md file already exists.")
        return None
    
    try:
        pdf_text = extract_text(pdf_path)
        nchar = len(pdf_text)
        log = f"{output_name} {nchar:<7} {pdf_path}\n"
        print(log)
        write_file(output_dir + "pdf_to_md.log", log, mode="a")
        write_file(output_file, pdf_text)
        return output_name, nchar
    except Exception as e:
        log = f"Error processing {pdf_path}: {str(e)}\n"
        print(log)
        write_file(output_dir + "pdf_to_md.log", log, mode="a")
        return None

def sumarize_article_text(agent, fname, prompt, input_dir, output_dir, bStream=False, ncharmax=300000):
    """
    Callback for processing a single .md file and feeding it to LLM.
    """
    txt = read_file(input_dir + fname)
    task = prompt + txt
    nchar = len(task)
    
    if nchar >= ncharmax:
        log = f"{fname} too long: nchar={nchar}\n"
        print(log)
        write_file(output_dir + "md_files_to_llm.log", log, mode="a")
        return
    
    if bStream:
        for chunk in agent.stream(task):
            print(chunk, flush=True, end="")
        result = agent.assistant_message
    else:
        result = agent.query(task)
    
    write_file(output_dir + fname, result)

if __name__ == '__main__':
    input_dir    = "/home/prokop/Desktop/PAPERs/" 
    out_dir      = '/home/prokop/Desktop/PAPERS_meta/'
    output_dir_1 = out_dir+'fulltexts/'
    output_dir_2 = out_dir+'summaries/'

    pdf_list_file = output_dir_1 + "pdf_file_list.log"
    md_list_file  = output_dir_2 + "md_file_list.log"

    pdf_log_file  = output_dir_1 + "process_pdf_files.log"
    md_log_file   = output_dir_2 + "process_md_files.log"
    
    # Step 1: Find PDFs and save the file paths
    pdf_files = find_files(input_dir, relevant_extensions={'.pdf'}, saveToFile=pdf_list_file)
    # Step 2: Process PDFs to .md files in parallel
    process_files_parallel(pdf_files, pdf_to_md, pdf_log_file, output_dir_1)

    # # Step 3: Find .md files and save the file paths
    # md_files = find_files(output_dir_1, relevant_extensions={'.md'}, saveToFile=md_list_file)
    # prompt = read_file("../prompts/sumarize_article_pdf.md")
    # # Step 4: Process .md files to LLM
    # agent = AgentOpenAI("fzu-llama-8b")
    # process_files_serial(md_files, lambda f, out, i: sumarize_article_text(agent, f, prompt, output_dir_1, output_dir_2), md_log_file, output_dir_2)
