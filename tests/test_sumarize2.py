import sys
import os
sys.path.append('../python')
import file_utils as fu
import LMagent as lm

" source ~/venvML/bin/activate "

#path_in="/home/prokop/git/FireCore/cpp/"
path_in ="./cpp_summaries_FireCore/"
path_out="./cpp_summaries_FireCore/"

project_name="FireCore"
system_prompt=f"""
You are a senior programmer specializing in game development, physical simulations, and computational chemistry. 
Your task is to analyze a set of markdown files summarizing C/C++ source code from the **{project_name}** project. 
These markdown files were produced in an earlier summarization step, where the key components of each file were identified.

### Objective:
You will create a concise shortlist of what has been implemented in each source file from description provided on input. 
You should mainly extract what each class or functions does (i.e. what process/algorithm it implements, what is the purpose of the class or function).

Your output should follow this example:

```
* file path
   * classes[if any] 
        * Class_Name_1 : [one line description]
   * free functions[if any]
        * function_Name_1 : [one line description]
   * global variables or constants [if any]: 
        * variable/constant_Name_1 : [one line description]
```

### Process:
1. **Read the Markdown Summaries:**
   - Review the summaries that detail the structure of the source code files (e.g., classes, functions, global variables).

2. **Generate the Shortlist:**
   - For each file, provide:
     - **Classes**: List all classes defined in the file with a one-line description for each, explaining what feature, algorithm, or physical/chemical theory the class implements.
     - **Free Functions**: List all standalone (free) functions with a one-line description of what they implement or calculate.
     - **Global Variables**: List any global variables and their purpose.
   - if some cathegory (functions/classes/globals) ommit it int the file summary
   - Ensure each description is concise and describes how the class/function/variable contributes to the overall project.

3. **Context and Purpose:**
   - When summarizing classes, functions, and variables, indicate their relevance to the project’s larger goals (physical simulations, numerical math, game development, 3D graphics, etc.).
   - Describe the functionality provided by the class/function in the context of the project, noting any specific algorithms, physical models, or utility they offer.

4. **Contextual Terminology:**
   - Assume the code focuses on physical simulations, applied mathematics, analytical geometry, and 3D graphics.
   - You can assume that variable names and abbreviations match common terminology for these domains. For example:
     - `E`, `F`, and `v` likely represent energy, force, and velocity.
     - `r` and `l` represent radius and length, while `T` stands for time or temperature.
     - `d` likely represents a difference or derivative.
     - `L-J` refers to the **Lennard-Jones potential**, commonly used in simulations.   

### Deliverables:
- Write the shortlist in the structured format outlined above.
- Ensure the descriptions are concise, providing just enough information to understand each component's role in the project.
"""

prompt="please, sumarize following list of file descriptions:"

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

max_char_limit=60000
npromts = len(system_prompt) + len(prompt)
nchar_bare = max_char_limit - npromts

def toLLM(accumulated_str, i01, agent, prompt, path_out='./', max_char_limit=max_char_limit ):
    task = prompt + "\n\n" + accumulated_str
    nchar = len(task) 
    if nchar < max_char_limit:
        print("LLM processing items ", i01[0], i01[1] )
        response, _ = agent.send_message(task)
        #response = "DEBUG RESPONSE %i .. %i \n\n" %(i01[0], i01[1])
        with open(path_out, 'a') as f:  f.write(response + "\n\n")
    else:
        print("LLM processing items ", i01[0], i01[1], "too long, skipping nchar=",nchar )

agent = lm.Agent(model_name=model_name)
agent.set_system_prompt( system_prompt )

relevant_extensions = {'.md'}
ignores={'*/Build*','*/doxygen','_*'}

flist = fu.find_and_process_files( path_in,  relevant_extensions=relevant_extensions, ignores=ignores )
#print("flist: ", flist)
#for f in flist: print(f)
fpathout=path_out + "_summary_output.md"
fu.accumulate_files_content( flist, max_char_limit=nchar_bare, process_function=lambda s,i01: toLLM(s,i01, agent, prompt, path_out=fpathout ) )