# `ForceField.h`

# includes

* `fastmath.h` - fast (approximative) mathematical functions.
* `Vec3.h` - definitions for 3D vectors.
* `Mat3.h` - definitions for 3x3 matrices.
* `Forces.h` - definitions for various force-related functions.

# Classes

### `Atoms`

This class represents some system like a molecule or a crystal.

##### Properties

* `natoms` : `int` - Number of atoms in the system.
* `atypes` : `int[]` - Array of atom types.
* `apos` : `Vec3d[]` - Array of atom positions.
* `lvec` : `Mat3d` - lattice vectors (a,b,c)

##### Methods

* `clone` : creates a new instance of the class with the same contents as the original.
* `print` : prints the contents of the class.
* `save_xyz` : saves the contents of the class to an XYZ file.
* `load_xyz` : loads the contents of the class from an XYZ file.

### `ForceField` 

This class represents a generic (abstract) force field for a system of atoms.

##### Artibutes 

* extends `Atoms`

##### Properties

* `Etot` : `double` - total energy of the system.
* `aforces` : `Vec3d[]` - array of forces acting on atoms.
* `avelocity` : `Vec3d[]` - array of velocities of atoms.
* `mass` : `double[]` - array of masses of atoms.

##### Methods

* `eval` : `abstract` - evaluate energy and forces in the system.
* `move` : `abstract` - update the positions of atoms in the system.
* `run` - run the simulation (dynamics, relaxation, etc.).

### `NonBodningFF` 

This class represents a non-bonding force field for a system of atoms. Implemented 

##### Artibutes 

* extends `ForceField`

##### Properties

* `bOMP` : `bool` - flag for OpenMP parallelization.
* `Rcut` : `double` - cutoff radius for short-range non-bonding interactions.
* `Model` : `int` - model for non-bonding interactions ( 0 for Lennard-Jones, 1 for Morse, 2 for Buckingham ).
* `REQ` : `Vec3d[]` - Array of non-covalent interaction parameters {R0,E0,Q} for Coulomb and Lennard-Jones or Morse.
* `groups` : `Buckets3D` - partitioning of atoms into groups for accelerating short-range non-bonding interactions.


##### Methods

* `eval_NB_brute`  : evaluate non-bonding forces by simple O(N^2) algorithm.
* `eval_NB_groups` : evaluate non-bonding forces using groups for accelerating short-range non-bonding interactions.
* `eval` : `override` - evaluate energy and forces in the system.

# Free Functions

*  `getLJ` - evaluate Lennard-Jones potential.
*  `getMorse` - evaluate Morse potential.
*  `getBuck` - evaluate Buckingham potential.