import sys
sys.path.append('../python')
import LMagent as lm

"source ~/venvML/bin/activate"

path_in  = './Cpp_Train/CodeExamples/'
path_out = './Cpp_Train/CodeErrors/'

filename_pattern = 'commit_*.md' 

system_prompt="""
You are a senior teacher of scientific programming in C/C++.
Your task is to create a set of programming exercises for students to spot errors in the code.
You are given a C/C++ code which is functionaly correct and tested, and you identify places where people often make mistakes.
Such places are often related to:
 * boundary conditions (index near then end of array or boundary of a similation domain)
 * one off index (0 vs 1 array indexing)
 * uninitialized variables
 * generally things which can cause segmentation faults or undefined behavior
 * memory leaks
Write a short list of places prone to such errors. 
After idetifying such places, you generate several examples of errorous code, where you gently and secretely introduce the errors, so that the students will have to spot them.
However, you should introduce these errors in a way which is not obvius to the students. The more subtle the error, the better. Also the errors should not be captured by the compiler (i.e. should not generate compile-time errors nor warnings).

Each example should have a form of one modified function from the original code base. 
After each such example, you should provide a short explanation where exactly the error is, and what problem it will cause.
"""

prompt="please, generate 5 subtly errorous code examples from the following code:\n\n"

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
#model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

fname = "EwaldGrid.h"

with open(  path_in + fname, 'r') as f: code_in = f.read()

task = prompt + code_in
    
agent = lm.Agent(model_name=model_name)
agent.set_system_prompt( system_prompt )
with open( path_out + 'task.md', 'w') as f: f.write(task)
response,_ = agent.send_message( task );
with open( path_out + 'Error_Examples.md', 'w') as f: f.write(response)


