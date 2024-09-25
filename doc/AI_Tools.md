
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