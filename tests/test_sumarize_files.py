import os
from pyCruncher import file_utils as fu
from pyCruncher.AgentOpenAI import AgentOpenAI

" source ~/venvML/bin/activate "

path_in="/home/prokop/git/FireCore/cpp/"
#path_in="/home/prokop/git/SimpleSimulationEngine/cpp"
path_out="./cpp_summaries_FireCore/"


system_prompt="""
You are helful assistant and a senior programmer of physical simulations and computational chemistry.
"""

prompt="""
You are given a C/C++ source code which you should analyze and summarize into markdown file.
First try to understand the code and the overall purpose of the module, class or program implemented in the file. What is the role of this file in the project?
Then identify all global or class-level variables and identify their purpose.
List those variables and write one line for each of them.
Then identify all functions and methods and their purpose.
List those functions and methods and write one line for each of them.
Write everything in concise structured way, using bullet points.
You may assume that the code focus mostly on physical/chemical simulations and applied mathematics. Therefore assume terminology and abbreviations which are appropriate for this domains.
For example:
* `E`,`F`,`v` are probably energy, force and velocity.
* `r` and `l` are radius. `T` is temperature or time.
* `d` is probably difference or derivative.
* `L-J` is probably Lennard-Jones potential.

please, sumarize commits( %i .. %i ) contained in the following text:
"""

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

# ======= Functions

def toLLM(file_path, agent, max_char_limit=32768 ):
    flog = open( path_out + 'skipped.log', 'a')
    file_size = os.path.getsize(file_path)
    promt_size = len(system_prompt) + len(prompt)
    bProcessed = False
    if (file_size+promt_size) > max_char_limit:
        s = f"Skipping {file_path}, file is too large ({file_size} bytes)."
        print(s)
        flog.write( s+"\n" )
    else:
        with open(file_path, 'r') as f: content = f.read()
        task = (prompt %file_path) + "\n\n" + content
        fname = os.path.basename(file_path)
        # Process the file content (in this example, just check if content length exceeds the limit)
        if ( len(task) + len(system_prompt) + 2 )  < max_char_limit:
            print( "LLM process ", file_path )
            response,_ = agent.send_message( task );
            with open( path_out + fname + '.md', 'w') as f: f.write(response)
            bProcessed = True
        else:
            s = f"File {file_path} exceeds the character limit after reading (length: {len(content)} chars)."
            print( s )
            flog.write( s + "\n" )
    flog.close()

def clean_skipped( fnamein, fnameout ):
    pre = "/home/prokop/git/FireCore/cpp/"
    npre = len(pre)
    dct = {}
    with open( fnamein, 'r') as f:
        for line in f:
            ws = line.split()
            fname = ws[1][npre:-1]
            nbyte = ws[-2][1:]
            #print(fname, nbyte)
            #lst.append( (fname,int(nbyte)) )
            dct[fname] = int(nbyte)
    # sort by 2nd item
    lst = list( dct.items() )   #;print(lst)
    lst = sorted( lst, key=lambda x: x[1], reverse=True)
    #print(lst)
    #for fname,nbyte in lst: print(fname, nbyte)
    with open( fnameout, 'w') as f:
        for fname,nbyte in lst:
            # write alligned in columns, 100 chars for fname
            f.write(f"{fname:<100} {nbyte}\n")

# =============================
# ============= Body ==========
# =============================

#for f in flist: print(f)

# # ---- 1st round of sumarization of source code files
agent = AgentOpenAI(model_name)
# agent.set_system_prompt( system_prompt )
# relevant_extensions = {'.h', '.c', '.cpp', '.hpp'}
# ignores={'*/Build*','*/doxygen'}

#flist = fu.find_files( path_in, process_file=lambda f: toLLM(f, agent),  relevant_extensions=relevant_extensions, ignores=ignores )

#clean_skipped( path_out + 'skipped.log', path_out + 'skipped_clean.log' )

# initAgent( base_url="https://api.deepseek.com", api_key=None, key_file="./deepseek.key" )
# stream_response( prompt, system_prompt, agent=None ):
# get_response( prompt, system_prompt, agent=None  ):


agent = lm.initAgent( base_url="https://api.deepseek.com", key_file="./deepseek.key" )
with open( path_out + 'skipped_clean.log', 'r') as f:
    pre = "/home/prokop/git/FireCore/cpp/"
    for line in f:
        ws = line.split()
        filepath = pre+ws[0]
        print( "\n=====================\n", filepath, " "*(100-len(filepath)), ws[1], "\n=====================\n" )

        with open( filepath, 'r') as f: content = f.read()

        task = prompt + "\n\n" + content
        #for part in lm.stream_response( prompt=task, system_prompt=system_prompt, agent=agent ):
        #    print(part, end='', flush=True)  # Print each part as it comes in

        response = lm.get_response( prompt=task, system_prompt=system_prompt, agent=agent  )

        fname = filepath.split('/')[-1]
        fnameout = path_out + fname + '.md'
        print("respponse saved to file: ", fnameout )
        with open( fnameout, 'w') as f: f.write(response)
