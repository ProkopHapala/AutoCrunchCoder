
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
