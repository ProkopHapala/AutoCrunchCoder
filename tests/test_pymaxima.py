

import subprocess

'''
Help:
* lines which end with $ (instead of ;) are silent (no output printed)
'''

task="f:integrate(x*(1-x), x)$ g:exp(x^2+y^2+z^2)$ fg:f*g;"

command = f"""
display2d: false$
{task}
quit();
"""

process       = subprocess.Popen(['maxima', '--very-quiet'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
output, error = process.communicate(input=command.encode())
output_text   = output.decode().strip()

print( output_text )