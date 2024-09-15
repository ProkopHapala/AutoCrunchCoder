import sys
import os
sys.path.append('../python')
import file_utils as fu
import LMagent as lm

" source ~/venvML/bin/activate "

path_in="/home/prokop/git/FireCore/cpp/"
#path_in="/home/prokop/git/SimpleSimulationEngine/cpp"
path_out="./cpp_summaries/"


system_prompt="""
You are a senior programmer of physical simulations and computational chemistry.
You are given a C/C++ source code which you should analyze and summarize into markdown file.
First try to understand the code and the overall purpose of the module, class or program implemented in the file. What it the role of this file in the project?
Then identify all globl or class-level variables and identify their purpose.
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
"""
prompt="please, sumarize commits( %i .. %i ) contained in the following text:"

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

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
        task = prompt + "\n\n" + content
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


#for f in flist: print(f)

agent = lm.Agent(model_name=model_name)
agent.set_system_prompt( system_prompt )

relevant_extensions = {'.h', '.c', '.cpp', '.hpp'}
ignores={'*/Build*','*/doxygen'}

flist = fu.find_and_process_files( path_in, process_file=lambda f: toLLM(f, agent),  relevant_extensions=relevant_extensions, ignores=ignores )