import os
from pyCruncher import file_utils as fu
from pyCruncher.AgentOpenAI import AgentOpenAI

" source ~/venvML/bin/activate "

path_in="/home/prokop/git/FireCore/fortran"
#path_in="/home/prokop/git/SimpleSimulationEngine/cpp"
path_out="/home/prokop/git/AutoCrunchCoder/tests/cpp_summaries_FireBall/"


system_prompt="""
You are an experienced senior programmer specializing in physical simulations and computational chemistry. You are tasked with analyzing and summarizing a Fortran source code file from **Fireball**, a local basis set (LCAO) density functional theory (DFT) tight-binding program. The code uses a numerical basis set with finite support, where all integrals are pre-calculated and stored in a lookup table for interpolation.

### Objective:
Your task is to understand the provided code and create a structured, concise summary in a markdown file. Follow these guidelines:

1. **Analyze Code Purpose:**
    - Determine the overall purpose of the file/module.
    - Identify the role this file plays within the larger Fireball DFT program.
    - Specify whether it contains subroutines, module definitions, or global variable definitions.

2. **Variables and Scope:**
    - List and categorize important variables:
        - **Local Variables**: Defined within subroutines.
        - **Global Variables**: Defined in modules or elsewhere.

3. **Subroutine Purpose and Algorithm:**
    - For each subroutine, determine:
        - Its physical or chemical meaning.
        - The algorithm implemented.
        - How it fits into the broader DFT workflow.
        - specify of what other subroutines this subroutine depends on and how.
            - Be concise - one bullet point of sentence per one dependency.

4. **Sub-Tasks in DFT:**
    When relevant, link the subroutines and algorithms to core DFT operations, such as:

    - **Self-Consistency Loop (SCF):**
        1. **Assembling Hamiltonian (H) and Overlap (S) Matrix:**
            - Interpolation from the integral data table.
            - Transformation from Cartesian to bond-oriented coordinates.
            - Assembling interactions (short-range, long-range Coulomb, exchange-correlation functionals like Ceperley-Alder (CA), pseudopotentials, etc.).
            - Derivatives for force calculations.
        2. **Solving the Schrödinger/Kohn-Sham Equations:**
            - Transformation of H and S matrices from real space to reciprocal space.
            - Diagonalization of the overlap matrix for the Löwdin transformation.
            - Diagonalization of the Hamiltonian matrix to obtain eigenvalues and eigenvectors.
        3. **Building the Density Matrix:**
            - Applying Fermi-Dirac occupation to set the occupancy of eigenstates.
            - Constructing the density matrix from eigenvectors.
            - Projecting the density matrix onto atomic charges.

5. **Terminology:**
    Assume standard abbreviations and terminology from physical and chemical simulations:
    - **E**, **F**, and **v** typically represent energy, force, and velocity.
    - **r** and **l** are radius and length, while **T** represents time or temperature.
    - **d** likely represents difference or derivative.
    - **H**, **h_mat**, **S**, and **s_mat** likely represent the Hamiltonian and overlap matrices.

Write the summary in a concise structured, bullet-point format suitable for professionals in computational chemistry and applied mathematics.
"""
prompt="please, sumarize following file %s in the following text:"

#model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

def toLLM(file_path, agent, max_char_limit=65000 ):
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


#for f in flist: print(f)

agent = AgentOpenAI(model_name)
agent.set_system_prompt( system_prompt )

relevant_extensions = {'.f90'}
ignores={'*/Build*','*/doxygen'}

flist = fu.find_files( path_in, process_file=lambda f: toLLM(f, agent),  relevant_extensions=relevant_extensions, ignores=ignores )
