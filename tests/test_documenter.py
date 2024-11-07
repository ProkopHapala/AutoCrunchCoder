import os, shutil, sys
sys.path.append("../")

#from pyCruncher import ctags
from pyCruncher.CodeDocumenter import CodeDocumenter


#/home/prokophapala/git/FireCore/cpp/common/molecular/MolWorld_sp3_simple.h.bak
#/home/prokophapala/git/FireCore/cpp/common/molecular/MolWorld_sp3_simple.h.bak

def get_backups( fnames, path ):
    # copy from backup *.bak
    for f in fnames: 
        f_bak = path + f + ".bak.h"
        if os.path.exists(f_bak):
            fo = path + f
            if os.path.exists(fo): os.remove(fo)
            #os.copy(f_bak, f)
            shutil.copy(f_bak, fo)
        else:
            print(f"File {f} does not exist!")

if __name__ == "__main__":
    documenter = CodeDocumenter( context_strategy="whole_file" )
    #documenter = CodeDocumenter( context_strategy="body" )
    #project_path = "/home/prokop/git/FireCore/cpp"
    #project_path = "/home/prokophapala/git/FireCore/cpp"
    project_path = os.path.expanduser("~/git/FireCore/cpp")
    selected_files = ["/common/molecular/MolWorld_sp3_simple.h"]
    get_backups( selected_files, project_path )
    documenter.process_project(project_path, selected_files )