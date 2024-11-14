import sys
import os

sys.path.append("../")
from pyCruncher.AgentOpenAI   import AgentOpenAI
from pyCruncher.AgentGoogle   import AgentGoogle
from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test( bStream=False, template_name="deepseek-coder", prompt="Write function double getLJ(Vec3d dij, Vec2d RE, Vec3d& force) in C++ which calculate energy and force using Lennard-Jones potential. dij=pi-pj is vector between the atoms, RE{R0,E0} are energy minimum E0 and equilibrium distance R0. Keep it concise, generate just code, <20 lines, no bulshit around." ):
    """
    Selection of agent models:

    deepseek-coder
    gemini-flash
    gemini-pro
    claude-sonnet
    claude-haiku
    codestral
    mistral
    groq-llama-70b
    groq-llama-8b
    samba-llama-70b
    cerebras-llama-70b
    fzu-llama-8b
    fzu-Qwen25-32b
    fzu-Codestral-22b
    fzu-DeepSeek-V2CL
    """

    if "deepseek" in template_name:
        agent = AgentDeepSeek( template_name=template_name )
        #print("Available models:", agent.client.models.list())
    elif "gemini" in template_name:
        agent = AgentGoogle( template_name=template_name )
    else:
        agent = AgentOpenAI( template_name=template_name )
        #print("Available models:", agent.client.models.list())

    print("\nuser:  "+prompt+"\n")
    print("\nagent: "+"\n")
    if bStream:
        for chunk in agent.stream(prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query(prompt)
        print(result.content)
        with open("debug_LLM_answer.md", "w") as f:  f.write(result.content)

if __name__ == "__main__":
    #test( bStream = True, template_name="gemini-flash" )
    #test( bStream = True, template_name="codestral" )
    #test( bStream = False, template_name="codestral" )
    #test( bStream = False, template_name="mistral" )
    #test( bStream = False, template_name="groq-llama-70b" )
    #test( bStream = False, template_name="samba-llama-70b" )
    #test( bStream = False, template_name="cerebras-llama-70b" )
    #test( bStream = False, template_name="grok" )
    #test( bStream = False, template_name="github-GPT4o-mini" )
    #test( bStream = False, template_name="openrouter-GPT4o-mini" )
    test( bStream = False, template_name="hyperbolic-Qwen25-32b" )

    

    #test( bStream = True )
    #test( bStream = False )