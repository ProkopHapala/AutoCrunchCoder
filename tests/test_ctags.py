
import sys
sys.path.append("../")
from pyCruncher import ctags as ct

src_path = "/home/prokophapala/git/FireCore/cpp"

exclude=[ "common_resources", "Build", "Build-asan", "Build-opt", "Build-dbg" ]


#ct.run_ctags( "tags_all.md", src_path, exclude=exclude )

files_dict, classes_dict = ct.process_ctags_json("tags_all.md")

ct.print_file_dict( files_dict , end="")
ct.print_class_dict( classes_dict , end="")


# for k,v in files_dict.items():
#     print("file: ", k)
#     print('== classes')
#     for m in v['classes'  ]: print("    ", m)
#     print('== functions')
#     for f in v['functions']: print("    ", f)  
#     print('== globals')
#     for g in v['globals'  ]: print("    ", g)  

# for k,v in classes_dict.items():
#     print("class: ", k)
#     print("== Methods:"); 
#     for m in v['methods'   ]: print("   ", m)
#     print("== properties:"); 
#     for p in v['properties']: print("   ", p)

#ct.generate_ctags_files( src_path, exclude = exclude )

#files_dict, classes_dict = ct.construct_dictionaries()

# Display the results
# import pprint
# pprint.pprint(files_dict)
# pprint.pprint(classes_dict)