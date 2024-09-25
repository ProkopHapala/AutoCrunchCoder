#!/bin/bash

# NOTE: install package universal-ctags
# sudo apt-get install universal-ctags

path=/home/prokophapala/git/FireCore/cpp/

#FLAGS="--languages=C++ --exclude=common_resources --exclude=Build* --exclude=.git --extra=+fq"
FLAGS="--languages=C++ --exclude=common_resources --exclude=Build --exclude=Build-asan --exclude=Build-opt --exclude=Build-dbg --extra=+fq"

ctags -R $FLAGS -o tags $path

# 1. Export Free Functions
# Using --kinds-c++=f to export only functions
ctags -R --kinds-C++=f $FLAGS -o tags_free_functions  $path

# 2. Export Global Variables
# Using --kinds-C++=v to export global variables
ctags -R --kinds-C++=v $FLAGS -o tags_global_variables $path

# 3. Export Classes
# Using --kinds-C++=c to export only classes
ctags -R --kinds-C++=c $FLAGS -o tags_classes $path

# 4. Export All Class Members (methods and properties)
# --kinds-C++=m exports all members
ctags -R --kinds-C++=m $FLAGS -o tags_all_class_members $path

# 5. Export Only Methods
# Extracting methods from all members, using regex to detect methods (with parentheses)
grep -P '\(' tags_all_class_members > tags_class_methods

# 6. Export Only Properties
# Filter out lines with parentheses (methods) to keep only properties
grep -vP '\(' tags_all_class_members > tags_class_properties
