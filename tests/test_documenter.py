import os
import sys
sys.path.append("../")

#from pyCruncher import ctags
from pyCruncher.CodeDocumenter import CodeDocumenter

#from code_documenter import CodeDocumenter
#import ctags

# def document_selected_files(project_path: str, selected_files: list):
#     # Generate tags
#     tags_file = "tags_all.json"
#     ctags.run_ctags(tags_file, project_path)

#     # Process tags
#     classes, free_functions = ctags.process_ctags_json(tags_file, project_path)

#     # Initialize documenter
#     documenter = CodeDocumenter(agent_type="deepseek")

#     # Process selected files
#     for file_path in selected_files:
#         rel_path = file_path[len(project_path):].lstrip('/')
#         print(f"Processing file: {rel_path}")
        
#         # Document free functions in this file
#         for func_name, func_locations in free_functions.items():
#             if rel_path in func_locations:
#                 print(f"  Documenting free function: {func_name}")
#                 func_info = func_locations[rel_path]
#                 func_info['name'] = func_name  # Add name to info dict
#                 documenter.document_function(func_info, file_path)
        
#         # Document class methods in this file
#         for class_name, class_info in classes.items():
#             for (_, file_), class_data in class_info.items():
#                 if file_ == rel_path:
#                     print(f"  Documenting methods of class: {class_name}")
#                     for method_name, method_info in class_data['methods'].items():
#                         method_info['name'] = method_name  # Add name to info dict
#                         method_info['scope'] = class_name  # Add scope to info dict
#                         documenter.document_function(method_info, file_path)

# # Usage example
# if __name__ == "__main__":
#     project_path = "/home/prokop/git/FireCore/cpp"
#     selected_files = [
#         "/home/prokop/git/FireCore/cpp/MolWorld_sp3.cpp",
#         "/home/prokop/git/FireCore/cpp/MMFF.cpp"
#     ]

#     document_selected_files(project_path, selected_files)


# def main():
#     # 1. Initialize documenter and verify LLM connection
#     documenter = CodeDocumenter(agent_type="deepseek")
#     if not documenter.setup_agent("deepseek"):
#         print("Failed to initialize LLM agent!")
#         return

#     # 2. Prepare and verify database
#     project_path = "/home/prokop/git/FireCore/cpp"
#     if not documenter.prepare_database(project_path):
#         print("Failed to prepare code database!")
#         return

#     # 3. Print database statistics
#     documenter.print_database_stats()

#     # 4. Select files to process
#     selected_files = [
#         "/home/prokop/git/FireCore/cpp/MolWorld_sp3.cpp",
#         "/home/prokop/git/FireCore/cpp/MMFF.cpp"
#     ]

#     # 5. Do a dry run first
#     # print("\nDoing dry run...")
#     # results = documenter.process_files(selected_files, dry_run=True)
#     # 6. Print results
#     # print("\nDry run results:")
#     # print(f"Successfully processed: {len(results['success'])} functions")
#     # print(f"Failed to process: {len(results['failed'])} functions")
#     # print(f"Skipped: {len(results['skipped'])} functions")

#     # 7. If dry run looks good, proceed with actual documentation
#     if input("\nProceed with documentation? (y/n): ").lower() == 'y':
#         results = documenter.process_files(selected_files, dry_run=False)
#         print("\nFinal results:")
#         print(f"Successfully documented: {len(results['success'])} functions")
#         print(f"Failed to document: {len(results['failed'])} functions")
#         print(f"Skipped: {len(results['skipped'])} functions")

# if __name__ == "__main__":
#     main()



# def document_project(project_path, selected_files=None):
#     """Main function to document the project"""
#     documenter = CodeDocumenter(agent_type="deepseek")

#     # 1. Initialize and verify LLM connection
#     if not documenter.setup_agent("deepseek"):
#         print("Failed to initialize LLM agent!")
#         return

#     # # 2. Prepare and verify database
#     if not documenter.prepare_database(project_path):
#         print("Failed to prepare code database!")
#         return

#     # 3. Print database statistics
#     #documenter.print_database_stats()

#     # 4. Process selected files
#     files_to_process = selected_files if selected_files else [project_path]

#     # for file_path in files_to_process:
#     #     rel_path = os.path.relpath(file_path, project_path)
#     #     print(f"\nProcessing file: {rel_path}")
        
#     #     # Document free functions
#     #     for func_name, func_locations in documenter.free_functions.items():
#     #         if rel_path in func_locations:
#     #             print(f"  Documenting free function: {func_name}")
#     #             func_info = func_locations[rel_path]
#     #             documenter.document_function(func_info, file_path)
        
#     #     # Document class methods
#     #     for class_name, class_info in documenter.classes_dict.items():
#     #         for (_, file_), class_data in class_info.items():
#     #             if file_ == rel_path:
#     #                 print(f"  Documenting methods of class: {class_name}")
#     #                 for method_name, method_info in class_data['methods'].items():
#     #                     documenter.document_function(method_info, file_path)

# # Document specific files
# project_path = "/home/prokop/git/FireCore/cpp"
# selected_files = [
#   "/home/prokop/git/FireCore/cpp/MolWorld_sp3.cpp",
#   "/home/prokop/git/FireCore/cpp/MMFF.cpp"
# ]

# document_project(project_path, selected_files)

# # Or document entire project
# # document_project(project_path)



def main():
    project_path = "/home/prokop/git/FireCore/cpp"
    selected_files = [
        "/common/molecular/MolWorld_sp3_simple.h"
        #"/common/molecular/MolWorld_sp3.h",
    ]

    # Initialize documenter
    documenter = CodeDocumenter(agent_type="deepseek")
    if not documenter.setup_agent("deepseek"):
        print("Failed to initialize LLM agent!")
        return
        
    # Prepare database
    if not documenter.prepare_database(project_path):
        print("Failed to prepare code database!")
        return
    
    #for k in documenter.files_dict: print( k )    # print all files
        
    # Process selected files
    for file_path in selected_files:
        print(f"\nProcessing file: {file_path}")
        documenter.document_file(file_path)

if __name__ == "__main__":
    main()