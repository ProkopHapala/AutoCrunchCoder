import os, sys
sys.path.append("../")

from pyCruncher.CodeDocumenter_md import CodeDocumenter_md

if __name__ == "__main__":
    documenter = CodeDocumenter_md()
    project_path = os.path.expanduser("~/git/FireCore/cpp")
    selected_files = ["/common/molecular/MolWorld_sp3_simple.h"]
    #documenter.process_project(project_path, selected_files, agent_type="deepseek" )
    documenter.process_project(project_path, selected_files, agent_type="gemini-flash" )
