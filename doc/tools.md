
* **Symbolic Math**
    * [Maxima](https://maxima.sourceforge.io/)
    * [Sympy](https://www.sympy.org/en/index.html)
        * [SymEngine](https://github.com/symengine/symengine)
        * [SymPyLive](https://live.sympy.org/)
* Automatic Differentiation
    * [JuliaDiff](https://juliadiff.org/)
    * [ForwardDiff.jl](https://github.com/JuliaDiff/ForwardDiff.jl)
* Numerical Quadrature
    * [quadpy](https://github.com/sigma-py/quadpy)
    * Julia
        * Integrals.jl is specifically designed for integration over common 2D and 3D shapes.
        * Cubature.jl and HCubature.jl are flexible and can be adapted for various domains through coordinate transformations.
* Static Code analysis 
    * [Clang](https://clang.llvm.org/docs/ClangStaticAnalyzer.html)
        * `clang --analyze`
    * [GCC](https://developers.redhat.com/articles/2022/04/12/state-static-analysis-gcc-12-compiler#toward_support_for_c__)
        * `gcc -fanalyzer`
        * [gcc/Static-Analyzer-Options](https://gcc.gnu.org/onlinedocs/gcc/Static-Analyzer-Options.html)
    * [Cppcheck](https://cppcheck.sourceforge.io/)
        * `cppcheck --enable=all --inconclusive`
* Assembly / Disassembly
    * [Gdb](https://www.gnu.org/software/gdb/)
    * `gcc   -S -fverbose-asm example.c -o example.s`
    * `gcc   -S -Ofast -fverbose-asm example.c -o example.s`
    * `gcc   -S -Ofast -fverbose-asm -fPIC -shared example.c -o example.s`
    * `clang -S -fverbose-asm example.c -o example.s`
    * `clang -S -Ofast -fverbose-asm example.c -o example.s`
    * `clang -S -Ofast -fverbose-asm -fPIC -shared example.c -o example.s`
* Abstract Syntax Tree
    * [CppAst](https://github.com/microsoft/cppast)
    * [libclang-dev]
        * `clang -Xclang -ast-dump -fsyntax-only example.c`
        * `sudo apt-get install libclang-dev`


### LLM Providers

* Fundation Model providers
    * [OpenAI](https://openai.com/)
    * [Anthropic](https://www.anthropic.com/)
    * [API doc](https://docs.anthropic.com/en/api/getting-started) 
    * [DeepSeek](https://platform.deepseek.com/usage)
        * models: deepseek-chat, deepseek-coder
        * price: $0.14 / $0.28 1M tokens
    * [Google AI studio](https://aistudio.google.com/app/)
    * [API doc](https://ai.google.dev/gemini-api/docs/quickstart?lang=python)
    * Models: Gemini 1.5 Pro/Flash (Experimental), Gemma 2B,9B,27B
    * [Mistral](https://console.mistral.ai/)

* Integrators
    * [openrouter](https://openrouter.ai/models)
    * [Hugging Face](https://huggingface.co/)

* Fast Inference
    * [Groq](https://console.groq.com/playground)
    * [sambanova](https://cloud.sambanova.ai/) 
        * models: Llama-3.1 (8B,70B,405B)
        * price: 
            * Llama-3.1-8B    0.1$ : 0.2$  / 1Mtok  
            * Llama-3.1-70B   0.6$ : 1.2$  / 1Mtok  
            * Llama-3.1-405B  5.0$ : 10.0$ / 1Mtok 


### LLM Theory
 
* [Understanding Modern LLMs via DeepSeek](https://planetbanatt.net/articles/deepseek.html) 

### Run LLMs locally

* run as LAN network server:
   * automatic11111 - webUI -  Stable Diffusion
      * [is_there_a_way_i_can_share_my_local_automatic1111/](https://www.reddit.com/r/StableDiffusion/comments/xtkovu/is_there_a_way_i_can_share_my_local_automatic1111/)
        `>> export COMMANDLINE_ARGS="--listen"; ./webui.sh`
      * [stable-diffusion-webui API](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API)


### Programing Assistands

* [Aider](https://github.com/paul-gauthier/aider)
* 

### AI for research articles

* [typeset.io](https://typeset.io/)
* [consensus](https://consensus.app/search/?synthesize=on)

### RAG (Retrieval Augmented Generation)


##### [LocalGPT](https://github.com/PromtEngineer/localGPT/)  
local RAG for PDF documents et. - chat with your personal pdf library

* [LocalGPT-vision](https://github.com/PromtEngineer/localGPT/tree/localGPT-Vision) 
    * [YouTube: Massive Update to Local GPT—Now with Vision Models!](https://www.youtube.com/watch?v=w5WGbUGAE3s)

##### PDF to text

* [pdftolatex](https://github.com/vinaykanigicherla/pdftolatex)
* [Nougat: Neural Optical Understanding for Academic Documents](https://github.com/facebookresearch/nougat)
    * [YouTube: This Open-Source Tool will make your PDFs LLM Ready](https://www.youtube.com/watch?v=mdLBr9IMmgI)

### LLM Tool Use

How To Tool use Tool calling using AI models

##### Ollama Tool-calling 
* https://ollama.com/blog/tool-support

##### OpenAI Tool-calling  
* [tools](https://platform.openai.com/docs/assistants/tools)
* [function-calling](https://platform.openai.com/docs/assistants/tools/function-calling)
* [code-interpreter](https://platform.openai.com/docs/assistants/tools/code-interpreter)

##### DeepSeek Tool-calling   
* [function_calling](https://platform.deepseek.com/api-docs/function_calling/)
* Formated Response
    * [prefix_completion](https://platform.deepseek.com/api-docs/chat_prefix_completion)
    * [Fill-in-the-middle](https://platform.deepseek.com/api-docs/fim_completion)
    * [Strict JSON output format](https://platform.deepseek.com/api-docs/json_mode)

##### Qwen Tool-calling   
* [Function Calling Qwen 2](https://qwen.readthedocs.io/en/latest/framework/function_call.html)

##### Google Gemini Tool-calling
* [Function calling tutorial (Python)](https://ai.google.dev/gemini-api/docs/function-calling/tutorial?lang=python)


### Fine Tuning

* [axolotl]( https://github.com/axolotl-ai-cloud/axolotl)


### Prompt Engineering

* [ell](https://github.com/MadcowD/ell) - ell is a lightweight, functional prompt engineering framework built on a few core principles:
    * `pip install ell-ai`


### Abstract Syntax Tree using Clang @ Python

```Python
import clang.cindex

# Set the path to your libclang shared library (if needed)
# clang.cindex.Config.set_library_file('/path/to/libclang.so')

def print_ast(node, indent=0):
    """
    Recursively print the AST starting from the given node.
    """
    # Print the current node's kind, spelling, and location
    print('  ' * indent + f'[{node.kind}] {node.spelling} (line {node.location.line}, col {node.location.column})')

    # Recursively print each of the node's children
    for child in node.get_children():
        print_ast(child, indent + 1)

def main():
    # Initialize the index and parse the C/C++ file
    index = clang.cindex.Index.create()
    translation_unit = index.parse('example.c')

    # Print the filename
    print(f'Parsed file: {translation_unit.spelling}\n')

    # Print the AST starting from the root node
    print_ast(translation_unit.cursor)

if __name__ == '__main__':
    main()
```


### Clang Analyze libraries

```
clang --analyze -I/home/prokophapala/git/FireCore/cpp/common/math/ -I/home/prokophapala/git/FireCore/cpp/common/ -I/usr/include/c++/11/ -I//usr/include/c++/11/bits/ -I/usr/include/x86_64-linux-gnu/c++/11/ /home/prokophapala/git/FireCore/cpp/common/molecular/NBFF.h


-I/home/prokophapala/git/FireCore/cpp/common/math/
-I/home/prokophapala/git/FireCore/cpp/common/
-I/usr/include/c++/11/
-I//usr/include/c++/11/bits/
-I/usr/include/x86_64-linux-gnu/c++/11/

```

### Symengine

```
>>> from symengine import var
>>> var("x y z")
(x, y, z)
>>> e = (x+y+z)**2
>>> e.expand()
2*x*y + 2*x*z + 2*y*z + x**2 + y**2 + z**2
```

### pymaxima

```
import pymaxima

# Start a Maxima session
maxima = pymaxima.interact()

# Send a command to Maxima
result = maxima.eval("integrate(x^2, x)")

# Print the result
print(result)
```

```
import subprocess

# Call Maxima with a simple command
process = subprocess.Popen(['maxima', '--very-quiet'],
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)

# Send a command to Maxima
command = "integrate(x^2, x); quit();\n"
output, error = process.communicate(input=command.encode())

# Decode and print the output
print(output.decode())
```