"""
Thin Python wrapper around the Maxima Computer Algebra System (CAS).

This is the pyCruncher2 reorganized version of pyCruncher/Maxima.py.
Maxima is used for symbolic differentiation, integration, and expression
simplification — the "ground truth" for verifying that LLM-generated
force-field code matches the intended physics equations.

Non-obvious things:
- Commands are sent to a Maxima subprocess via stdin; `display2d:false` turns
  off the pretty-printer so output is machine-parseable.
- Lines ending with `$` (instead of `;`) are silent — no output printed.
  Use `$` for intermediate assignments, `;` for results you want to read.
- `get_derivs()` computes energy E and all partial derivatives dE/dof in one
  batch call — much faster than calling Maxima separately for each derivative.
"""

import subprocess
import  time

'''
Help:
* lines which end with $ (instead of ;) are silent (no output printed)
'''

#task="f:integrate(x*(1-x), x)$ g:exp(x^2+y^2+z^2)$ fg:f*g;"

command_template = """
display2d: false$
%s
quit()$
"""

def run_maxima(code):
    process       = subprocess.Popen(['maxima', '--very-quiet', '-q'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    #process       = subprocess.Popen(['maxima','-q'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    command = (command_template %code)
    output, error = process.communicate(input=command.encode())
    if error:
        print(f"Error: {error.decode()}")
        return None
    output_text   = output.decode().strip()
    return output_text

def label_maxima_output(output, labesl, sep=':'):
    output_lines = output.split('\n')
    #print("len(output_lines) ", len(output_lines))
    #print(output_lines)
    labeled_output = []
    for i, line in enumerate(output_lines):
            label = labesl[i]
            labeled_output.append( label +"  "+sep+"   "+ line )
    #return '\n'.join(labeled_output)
    return labeled_output

def get_derivs( Eformula, DOFs ):
    code="E:"+Eformula+";\n"    
    labels=["E"]
    for i, var in enumerate(DOFs):
        #code+="factor(ratsimp(diff(E,"+var+")));\n"
        #code+="ratsimp(diff(E,"+var+"));\n"
        code+="diff(E,"+var+");\n"
        labels.append("dE_"+var)
    out = run_maxima( code )
    lout = label_maxima_output( out, labels )
    return lout

def run_maxima_script(script_content, timeout=10):
    try:
        # DEBUG: robust batch execution using subprocess.run with input
        if not script_content.endswith("\n"): # ensure Maxima receives a final newline
            script_content = script_content + "\n"
        completed = subprocess.run(["maxima", "-q"], input=script_content, capture_output=True, text=True, timeout=timeout)
        return completed.stdout, completed.stderr
        
            
        #     # Read output and error streams
        #     out_line = process.stdout.readline()
        #     err_line = process.stderr.readline()
            
        #     if out_line:
        #         stdout.append(out_line)
        #         start_time = time.time()  # Reset the timeout timer on output
            
        #     if err_line:
        #         stderr.append(err_line)
        #         start_time = time.time()  # Reset the timeout timer on output
            
        #     # Check if the process has been idle for too long
        #     t = time.time() - start_time
        #     print("time= ", t )
        #     if t > timeout:
        #         print("Subprocess seems to be waiting for input.")
        #         process.kill()
        #         break
        
        # # DEBUG: drain any remaining buffered output after process exit
        # if process.poll() is not None:
        #     rem_out, rem_err = process.communicate()
        #     if rem_out:
        #         stdout.append(rem_out)
        #     if rem_err:
        #         stderr.append(rem_err)
        
        # return ''.join(stdout), ''.join(stderr)
    
    except subprocess.TimeoutExpired:
        # DEBUG: subprocess.run timed out
        return None, "Maxima process timed out"