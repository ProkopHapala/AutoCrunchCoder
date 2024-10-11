
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyCruncher import ctags as ct

src_path = "/home/prokophapala/git/FireCore/cpp"

exclude = ["common_resources", "Build", "Build-asan", "Build-opt", "Build-dbg"]

#ct.run_ctags("tags_all.json", src_path, exclude=exclude)       # Generate ctags JSON file

ct.process_ctags_json("tags_all.json", src_path )


# json_file = 'tags_all.json'  # Replace with the actual JSON file path
# class_details = ct.parse_ctags_json(json_file)
# ct.display_class_details(class_details)

