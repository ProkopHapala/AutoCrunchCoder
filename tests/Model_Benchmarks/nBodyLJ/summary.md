## Task

**system_prompt**

You are a scientific programmer with deep knowledge of physics and mathematics and computer science.
You answer by concise code which you meticulously test and censider all possible edge cases.
You try to use you knowledge of mathematics to implement fast code with minimum overhead. 
You prefer to use simple data structures (plain arrays and pointers) and algorithms to maximize performance and readability.
You try to limit usage of pow(x,n). Instead use x*x and x*x*x etc.
You if costly functions like exp, log, sin, cos, tan are necessary, you try to precalculate the expression, store in variable and reuse it.

**prompt**

program C/C++ function which evaluates energy and force for n-body system of particles using Lenard-Jones + coulomb potential. 
* The function has this format:
```C++
double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const Vec3d* REQ ){ ... return E; };
```
where 
* apos is array of positions
* fapos is array of forces
* REQ is array of parameters { R0i, E0i, Qi }, mix them as R0ij=R0i+R0j; E0ij=E0i*E0j; Qij=Qi*Qj;
* R0ij is equilibrium distance between particles i and j, 
* E0ij is energy at equilibrium distance, 
* Qi*Qj is product of charges of particles i and j.
* Optimize the evaluation of LJ by substitution u=(R0/r) and precalculating the powers efficiently by multiplication, avoid using pow(x,n).

## Results

#### codestral

* Score: 9/10
* GOOD:
    * code seems correct
    * follows the instructions
    * generates concise efficient code
    * generate only code no bulshit text around
    * use efficient substitution: `u2 = R0ij*R0ij/r2`, `u6=u2*u2*u2`,  `u12=u6*u6`
* BAD:
    * does not use `Vec3d` efficiently (still works with scalars)

#### deepseek2    

* Score: 7/10
* GOOD:
    * code seems correct
    * efficinetl substitution `u=R0ij/r`, `u6=u*u*u*u*u*u`
* BAD:
    * generates a lot of bullshit text around
    * `u2=u*u; u6=u2*u2*u2` is more efficient than `u6=u*u*u*u*u*u;`
    * check `if(r>0)` is redudant
    * does not use `Vec3d` efficiently (still works with scalars)

#### Llama3.1      

* Score: 6/10
* GOOD:
    * efficient substitution `u=R0ij/r`, `u2=u*u, u3= u2*u, u6=u2*u2*u2, u12=u6*u6`
* BAD:
    * despite user request defined `double* REQ` rather than `Vec3d* REQ`
    * code is not concise
    * lot of bullshit text around

#### mathstral   

* Score: 4/10
* GOOD:
    * generates concise and efficient code
    * generate only code no bulshit text around
    * nice use of `Vec3d r` with vector math, although it is not consistent with definition of `Vec3d` (vector operators are not defined)
* BAD:
    * evaluation of force and energy is wrong
    * use `pow(r2,3)` despite dicouraged by user

#### Qwen2-Math    

* Score: 3/10
* GOOD:
    * text and equations seems mathematicaly sound
* BAD:
    * use lot of `pow()` functions even though user requested to avoid them
    * code seems wrong
    * code is hard to read and understand
    * split force and energy into two functions, which is inefficient, and not what user requested

#### internlm2.5   

* Score: 3/10
* GOOD:
    * code is concise
    * generates only code no bullshit text around
    * code seems logical with reasonable substitution `r=R0ij/dist;`
* BAD:
    * code is wrong
        * this is not Lenard-Jones potential:
        ```
            double u = R0ij / dist;
            double force_mag = 24 * E0ij * (u*u - 2*u + 1) / (dist*dist);
            E += 4 * E0ij * (u*u - 1);
        ```
    * strage / ilogical use of `Vec3d`
        * Why this? `Vec3d F[3] = {0};`  `F[0].x += dx * force_mag;`  

#### llava1.5      

* Score: 2/10
* GOOD:
    * code is concise
    * generates only code no bullshit text around
* BAD:
    * code is wrong 
        * `double r = apos[i].norm() + apos[j].norm()` is wrong
        * the Energy and Force evaluation does not match the equations for Lenard-Jones and Coulomb potentials
        ```
            double f = 1.0 / (4.0 * M_PI * pow(u, 3.0));
            E += f * (E0ij - Qij*pow(u, 2.0) - Qij*pow(u, 4.0));
        ```
    * use lot of `pow()` functions even though user requested to avoid them

#### deepseek-math"  (FAILED) - infinite loop

* Score: 0/10
* GOOD: nothing
* BAD: freezes in infinite loop

#### Qwen2_500M"   (FAILED) - infinite loop

* Score: 0/10
* GOOD: nothing
* BAD: freezes in infinite loop
