import sys
sys.path.append('../python')
import git_utils as gu
import LMagent as lm

"source ~/venvML/bin/activate"


path = './GitCommits/'

#ncommits = gu.process_all_commits( path = path )
#exit(0)

filename_pattern = 'commit_*.md' 

#callback = lambda s,i01: ( print("sumary ", i01[0], i01[1], "\n"+ "\n".join([line for line in s.splitlines() if "Commit" in line]) ),  exit() if i01[0]>3 else None )
#gu.accumulate_files(path, filename_pattern, 16000, callback)

# system_prompt="""
# You are a senior scientific programmer in domain of computational chemistry and materials science.
# You are given a markdown file with the content of several commits to a git repository.
# You should summarize the content of the commits - each commit is a single paragraph.
# Focus on what new features were added to the code and what bugs were fixed, and what problems are still open and unsolved.
# The goal it to note such information which will allow track the evolution of the code and the progress of the project.
# On second pass of your summary, you should be able to recostruct what is the cuurrent state of the code, what features are implemented and what are the open issues.
# Doing so consider that the code focus mostly on physical/chemical simulations and applied mathematics. Therefore your notes should use adequate terminology focused on these domains.
# """

system_prompt="""
You are a senior programmer.
You are given a markdown file with the content of several commits to a git repository.
You should summarize the content of the commits - each commit is a single short paragraph (max 100 words).
Focus on what new features were added to the code and what bugs were fixed, and what problems are still open and unsolved.
Clearly specify what is implemented in which file by bullet points. Prefer structured text over monolithic paragraphs.
The goal is to note such information which will allow track the evolution of the code and the progress of the project.
Only note informations which is visible form the `message` field of the commit and the changes in the files. NEVER fabulate or halucinate any information which is not clearly containted in the commit.
You may assume that the code focus mostly on physical/chemical simulations and applied mathematics. Therefore assume terminology and abbreviations which are appropriate for this domains.
For example: 
* `E`,`F`,`v` are probably energy, force and velocity. 
* `r` and `l` are radius. `T` is temperature or time. 
* `d` is probably difference or derivative. 
* `L-J` is probably Lennard-Jones potential.  
"""

prompt="please, sumarize commits ( %i .. %i ) contained in the following text:"

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
#model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

def process_text(agent,prompt,text,i01):
    print("sumary ", i01[0], i01[1], "\n"+ "\n".join([line for line in text.splitlines() if "Commit" in line] ) )
    task = ( prompt %(i01) ) + "\n\n" + text
    response,_ = agent.send_message( task );
    with open( path + 'summary_%04i-%04i.md' %(i01[0],i01[1]), 'w') as f: f.write(response)

agent = lm.Agent(model_name=model_name)
agent.set_system_prompt( system_prompt )


gu.accumulate_files(path, filename_pattern, 10000, lambda s,i01: process_text(agent,prompt,s,i01)   )