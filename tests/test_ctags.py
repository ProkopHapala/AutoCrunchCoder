
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyCruncher import ctags as ct

#src_path = "/home/prokophapala/git/FireCore/cpp"
src_path = "/home/prokop/git/FireCore/cpp"

exclude = ["common_resources", "Build", "Build-asan", "Build-opt", "Build-dbg"]

ct.run_ctags("tags_all.json", src_path, exclude=exclude)       # Generate ctags JSON file

#ct.process_ctags_json("tags_all.json", src_path )









# In your main script
classes, free_functions, files_dict = ct.process_ctags_json_claude("tags_all.json", src_path)

# Print file-based organization
ct.print_files_structure(files_dict)

# # You can also access information in different ways:
# # 1. By file:
# for file_path, content in files_dict.items():
#   print(f"Processing file: {file_path}")
#   # Access classes, methods, free functions in this file
  
# # 2. By class (as before):
# for class_name, class_info in classes.items():
#   print(f"Processing class: {class_name}")
#   # Access class methods and properties

# # 3. By free function:
# for func_name, func_locations in free_functions.items():
#   print(f"Processing function: {func_name}")
#   # Access function information



# json_file = 'tags_all.json'  # Replace with the actual JSON file path
# class_details = ct.parse_ctags_json(json_file)
# ct.display_class_details(class_details)

