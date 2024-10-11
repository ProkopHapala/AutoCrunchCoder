import sys
sys.path.append("../")

import subprocess

'''
Help:
* lines which end with $ (instead of ;) are silent (no output printed)
'''

#task="f:integrate(x*(1-x), x)$ g:exp(x^2+y^2+z^2)$ fg:f*g;"

task1="""; 
assume(a>0,b>0,x0>0);
slater(x0, a):= exp(-a*((x-x0)^2 + y^2 + z^2))/((x-x0)^2 + y^2 + z^2);
ss: slater(0.0,a)*slater(x0,b);
ss: ratsimp(expand(ss));
Syz: integrate(integrate(ss, y, -inf, inf), z, -inf, inf);
S: integral_x: integrate(integral_yz, x, -inf, inf); 
"""

task2="""; 
assume(a>0,b>0,x0>0);
ss: exp(-a*( x^2 + r^2))/( x^2 + r^2) * exp(-b*((x-x0)^2 + r^2))/((x-x0)^2 + r^2) * r;
ss: ratsimp(expand(ss));
Syz: integrate(ss, r, 0, inf)*2*%pi;
S: integral_x: integrate(integral_yz, x, -inf, inf); 
"""

task3="""; 
assume(a>0,b>0,x0>0);
ss: exp(-a*( x^2 + r^2))/( x^2 + r^2) * exp(-a*((x-x0)^2 + r^2))/((x-x0)^2 + r^2) * r;
ss: ratsimp(expand(ss));
Syz: integrate(ss, r, 0, inf)*2*%pi;
S: integral_x: integrate(integral_yz, x, -inf, inf); 
"""

command = f"""
display2d: false$
{task3}
quit();
"""

process       = subprocess.Popen(['maxima', '--very-quiet', '-q', '-batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
output, error = process.communicate(input=command.encode())
output_text   = output.decode().strip()

print( output_text )