#!/usr/bin/python

'''
Usage notes:

1) Activate Environement like this
>> source ~/venvML/bin/activate

2)In case of problems check the server status like this
>> curl http://localhost:1234/v1/models
'''

import sys
sys.path.append('../python')
import LMagent 
import Maxima


model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
# ======== Coder

# system_prompt="""
# You are scientific programmer inside automatic development loop. 
# The _user_ is a program. Therefore you must communicate with well structured messages, and precisely follow instructions. 
# Your answer must be in specific _format_ as prescribed by _user_.
# Mssages from _user_ will containt sections _feedback_,_errors_,_task_,_format_.
# _user_ will give you _task_ and you must generate code to solve it.
# Your answers will be automatically executed by _user_ checking for errors, and report back the result. 
# If there are errors you try several iterations to fix them.
# """

coder_system_prompt="""
You are a scientific programmer within an automated development loop.

The user is a program that requires well-structured communication. Your responses must be precise and adhere strictly to the instructions provided.
User messages will include sections: _feedback_, _errors_, _task_, and _format_.
Your primary role is to generate code based on the _task_ provided.
Your responses must follow the exact _format_ specified by the user.
After your code is executed by the user, you will receive _feedback_, including any _errors_. 
If _errors_ occur, you are expected to iterate and attempt to fix them until the solution is correct.
your asnwers should be concise, just code, without comments, using short variable names.
"""

coder_promt="""
In C++ Write a function: 
Vec4d Coulomb( Vec3d d_ij, Q_ij );
which calculates force and energy between two chaged particles. 
include "Vec3d.h" and "Vec4d.h" header files which implement classes Vec3d and Vec4d, do not reimplement them. 
Both Vec3d and Vec4d have functions dot(),norm(),norm2() and overloaded operators +,-,*, and +=,-=,*= ; 
Q_ij=Q_i*Q_j is product of charges of the two partices. 
d_ij=p_i-p_j is vector between the two particles.
the output Vec4d{ f.x,f.y,f.z,E } contains both force and energy.
"""  

# coder = LMagent.Agent(model_name=model_name)
# coder.set_system_prompt( coder_system_prompt )
#response = coder.send_message( coder_promt ); print("LM Studio: " + response)

# ======== Planner

planer_system_prompt="""
You are analyst and manager in scientific programming team within an automated development loop.

The user is a program that requires well-structured communication. Your responses must be precise and adhere strictly to the instructions provided.
User messages will include sections: _feedback_, _errors_, _task_, and _format_.
Your primary role is to layout a plan how to solve the provided _task_ by splitting it to simple sub-problems using different _tools_.
Your output should be a hierarchical to-do-list with clealy defined _sub-task_ as bullet point clearly stating which tools are used for that. 
Don't go technical details. You have at your disposal team of agents with varisous skills and tools. Your list should define _prompt_ for each agent.
The team _workers_ and _tools_ at your disposal are:
* Programer - can write code in (C/C++/OpenCL) and compile it in loop until it works
* Mathematician - can derive symbolic equations using Computer algebra system (Maxima/Sympy)
* Tester - can verify results by brute-force numerical evaluation using:
    * ForwardDiff.jl - Automatic Differentiation package
    * NumDeriv.jl    - Numerical Differentiation package
    * Integrate_Sphere.jl   - Numerical Integration in Spherical   Coordinates for cylindrically symmetric problems.
    * Integrate_Cylinder.jl - Numerical Integration in Cylindrical Coordinates for cylindrically symmetric problems.
"""

planer_promt="""
Make C++ library which calculates analytical overlap integrals between two atomic orbitals of Gaussian type. consider just orbitals s,p_x,p_y,p_z;
You must derive analytical expressions, implement them in C++ and test them using numerical integration.
R=(x,y,z);
R0=(x0,y0,z0);
r = |R-R0|   = sqrt((x-x0)^2+(y-y0)^2+(z-y0)^2);
psi_s(R0,w)  = Cs*exp(-r^2/w)
psi_px(R0,w) = Cp*psi_s(R0,w)*(x/r)
psi_py(R0,w) = Cp*psi_s(R0,w)*(y/r)
psi_pz(R0,w) = Cp*psi_s(R0,w)*(z/r)
the normalization constant Cs, Cp should be calculated from condition: <psi|psi>=1
"""  


# planer = LMagent.Agent(model_name=model_name)
# planer.set_system_prompt( planer_system_prompt )
# planer_response = planer.send_message( planer_promt ); #print("LM Studio: " + planer_response)
# with open("planer_response.md", "w") as f:f.write(planer_response)


# ======== Plan Critique


plan_critique_system_prompt="""
You are critique of project-plans in scientific programming team within an automated development loop.
You should go throu a project plan (hierarchical to-do-list of sub-taks) and check if it make sense and fit into big-picture. In particular check:
* if there are any missing sub-tasks
* if there are redundant sub-tasks
* if the order of tasks is correct
* if tasks are assigned to the right team members and tools
In case of a problem you should write a _NOTE_ to the particular sub-task.
In the end write a short summary, and quantification of the quality of the plan on the scale  of 1-10.
"""

plan_critique_promt="""
Make critique of the following plan:
"""
#plan_critique_promt += planer_response+"""\n The Task was: """+ planer_promt

# plan_critique = LMagent.Agent(model_name=model_name)
# plan_critique.set_system_prompt( planer_system_prompt )
# critique_response = plan_critique.send_message( plan_critique_promt ); #print("LM Studio: " + response)
# with open("critique_response.md", "w") as f:f.write(critique_response)


# ======== Mathematician pre-caution

premath_system_prompt=f"""
You are mathematician in scientific programming team. You are given mathematical problem, and you should analyze it with caution, and identify potential chalanges. 
* Consider possible singularities, limits and edge cases.
* For which range of parameters and variables is the problem well-defined. Are the parameters consedered to be real, complex, positive, negative, integers, rational, irrational, etc. ?
* Are there any symmetries or invariances in the problem worth explloiting ?
* In case of integrals consider which function are integrable, and well known mathematical tricks (substitution, integration by parts, transformation to other coordinates - polar, cylindrical, spherical, etc.) which can help.
"""

premath_system_prompt = """
You are a mathematician on a scientific programming team. Your task is to carefully analyze mathematical problems, identifying potential challenges and complexities. Focus on the following aspects:

1. **Singularities, Limits, and Edge Cases:**
   - Identify possible singularities and consider limits that might affect the problem.
   - Analyze edge cases and determine their impact on the overall solution.

2. **Parameter and Variable Domains:**
   - Determine the range of parameters and variables for which the problem is well-defined.
   - Specify whether parameters are assumed to be real, complex, positive, negative, integers, rational, irrational, etc.

3. **Symmetries and Invariances:**
   - Look for any symmetries or invariances in the problem that can be exploited to simplify the analysis or solution.

4. **Integration Considerations:**
   - For problems involving integrals, assess which functions are integrable.
   - Consider well-known mathematical techniques such as substitution, integration by parts, or coordinate transformations (polar, cylindrical, spherical, etc.) that may assist in solving the integral.

Approach the problem with a comprehensive and critical mindset, ensuring that all potential issues are considered and addressed.
"""

math_problem="""
Derive analytical expression for overlap integral <psi_i|psi_j> between two atomic orbitals of Gaussian type. Consider just s and p functions ( s,p_x,p_y,p_z ).
These are defined as:
psi_s  = Cs*exp(-r^2/w^2)
psi_px = Cp*psi_s*(x/r)
psi_py = Cp*psi_s*(y/r)
psi_pz = Cp*psi_s*(z/r)
where: 
* r = sqrt((x-x0)^2+y^2+z^2);
* x0 is shift of one of the gaussians with respect to the other
* w is width of the gaussian.
* Cs, Cp are normalization constants which can be calculated from condition: <psi|psi>=1

Note that Gaussian integral is not easy to calculate by naieve approch. Special method of Gaussian integral was developed by Gauss himself employing clever substitution to cylindrical coordinates.
"""

premath_promt="""
Critically analyze and asses following mathematical problem:
"""+math_problem

premath = LMagent.Agent(model_name=model_name)
premath.set_system_prompt( premath_system_prompt )
premath_response = premath.send_message( premath_promt ); print("LM Studio: " + premath_response)
with open("premath_response.md", "w") as f:f.write(premath_response)

premath_response = open("premath_response.md", "r").read()  

# ======== Mathematician

#CAS_name = "Maxima"
CAS_name = "SymPy"

mathematician_system_prompt=f"""
You are mathematician in scientific programming team within an automated development loop. 
Your job is to derive symbolic equations using Computer algebra system (Maxima/Sympy).
* You generate input code for {CAS_name} (generate just pure code without any comments or explanations)
* Your output code is executed in {CAS_name} and the output is returned to you in case of errors so you can re-iterate.
* The output of Maxima is then tested numerically by Tester. If it does not pass the tests, you will get the feedback from Tester, so you can re-iterate.
"""

mathematician_promt="""
Generate input for {CAS_name} to solve followng problem:
"""+math_problem+"""

Consider insights from previous analysis:

"""+premath_response

mathematician = LMagent.Agent(model_name=model_name)
mathematician.set_system_prompt( mathematician_system_prompt )
math_response = mathematician.send_message( mathematician_promt ); print("LM Studio: " + math_response)
with open("math_response.md", "w") as f:f.write(math_response)

# ========= SymPy

# code = open("math_response.md", "r").read()         #;print("SymPy code: " + code)
# #print("<<<<<<")
# code = LMagent.remove_code_block_delimiters(code)   #;print("SymPy code: \n" + code)
# with open("math_response.py", "w") as f:f.write(code)
# #print(">>>>>>")
# #exec(code)


# ========= Maxima

# # load code from file "math_response.md"
# code = open("math_response.md", "r").read()
#code = LMagent.remove_code_block_delimiters(code)  ;print("Maxima code: " + code)
#maxima_out = Maxima.run_maxima( code )             ;print("Maxima_out:\n", maxima_out)
#maxima_out = Maxima.run_maxima_script(code )       ;print("Maxima_out:\n", maxima_out)