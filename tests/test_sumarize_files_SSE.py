import os
from pyCruncher import file_utils as fu
from pyCruncher.AgentOpenAI import AgentOpenAI

" source ~/venvML/bin/activate "

path_in="/home/prokop/git/SimpleSimulationEngine/cpp/"
#path_in="/home/prokop/git/SimpleSimulationEngine/cpp"
path_out="./cpp_summaries_SimpleSimulationEngine/"


# system_prompt="""
# You are a senior programmer of games and simulations in physics chemistry.
# You are given a C/C++ source code which you should analyze and summarize into markdown file.
# The bigger goal is to document project "Simple Simulation Engine" to recall what is aready implemented in the project and allow easier navigation in the project.
# You will be given files one by one.
# First try to understand the code in each file and the overall purpose of the module, class or program implemented in the file. What is the role of this file in the project?
# Then identify all global or class-level variables and identify their purpose.
# List those variables and write one line for each of them.
# Then identify all functions and methods and their purpose.
# List those functions and methods and write one line for each of them.
# Write everything in concise structured way, using bullet points.
# You may assume that the code focus mostly on physical simulations, applied mathematics, analytical geometry, 3D graphics. Therefore assume terminology and abbreviations which are appropriate for this domains.
# For example:
# * `E`,`F`,`v` are probably energy, force and velocity.
# * `r` and `l` are radius. `T` is temperature or time.
# * `d` is probably difference or derivative.
# * `L-J` is probably Lennard-Jones potential.
# The anotation of "Simple Simulation Engine" is: a minimalistic engine for Physical simulations, Numerical math, Game development, Computer graphics, Educational purposes.
# NOTE: the code is not well documented and maintained, therefore do not consider all comments in the code completely thrustworthy, rather try to understant the C/C++ source code itself and deduce what is the meaning, and if it match the comments.

# Write the summary in a concise structured, bullet-point format suitable for professionals in computational chemistry and applied mathematics.
# """

system_prompt="""
You are a senior programmer specializing in game development, physical simulations, and computational chemistry.
You are tasked with analyzing and summarizing C/C++ source code files for a project called **"Simple Simulation Engine."**
The purpose of this task is to document the project, recall what has already been implemented, and improve navigation for future development.

### Objective:
Your task is to examine each source code file provided, understand its content, and produce a structured summary in markdown format. You will be given files one by one.

### Process:
1. **Understand the Code:**
   - Analyze the overall purpose of the file, including the role of any modules, classes, or programs implemented.
   - Identify how the file fits within the larger **Simple Simulation Engine** project.

2. **Global and Class-Level Variables:**
   - Identify all global and class-level variables.
   - For each variable, briefly describe its purpose (one line per variable).

3. **Functions and Methods:**
   - Identify all functions and methods.
   - For each function or method, briefly describe its purpose (one line per function/method).

4. **Contextual Terminology:**
   - Assume the code focuses on physical simulations, applied mathematics, analytical geometry, and 3D graphics.
   - Toy can assume that variable names and abbreviations match common terminology for these domains. For example:
     - `E`, `F`, and `v` likely represent energy, force, and velocity.
     - `r` and `l` represent radius and length, while `T` stands for time or temperature.
     - `d` likely represents a difference or derivative.
     - `L-J` refers to the **Lennard-Jones potential**, commonly used in simulations.

5. **Project Annotation:**
   - The **Simple Simulation Engine** is a minimalistic engine designed for:
     - Physical simulations
     - Numerical mathematics
     - Game development
     - Computer graphics
     - Educational purposes

6. **Handling Inconsistent Documentation:**
   - The code is not well-documented or maintained. Therefore, do not rely entirely on the comments within the code.
   - Focus on understanding the C/C++ source code itself, and use your analysis to determine the functionality, correcting or overriding comments when necessary.

### Deliverables:
- Summarize your findings in a **concise, structured, bullet-point format**.
- Ensure the summary is suitable for professionals in game development, 3D graphics, computational physics and chemistry, applied mathematics, or related fields.
"""



prompt="please, sumarize following file %s in the following text:"

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
        task = (prompt %file_path) + "\n\n" + content
        fname = os.path.basename(file_path)
        # Process the file content (in this example, just check if content length exceeds the limit)
        if ( len(task) + len(system_prompt) + 2 )  < max_char_limit:
            print( "LLM process ", file_path )
            response = agent.query(task)
            with open( path_out + fname + '.md', 'w') as f: f.write(response)
            bProcessed = True
        else:
            s = f"File {file_path} exceeds the character limit after reading (length: {len(content)} chars)."
            print( s )
            flog.write( s + "\n" )
    flog.close()


#for f in flist: print(f)

agent = AgentOpenAI("fzu-llama-8b")
agent.set_system_prompt( system_prompt )

relevant_extensions = {'.h', '.c', '.cpp', '.hpp'}
ignores={'*/Build*','*/doxygen'}

flist = fu.find_files( path_in, process_file=lambda f: toLLM(f, agent),  relevant_extensions=relevant_extensions, ignores=ignores )
