import os
import fnmatch

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def write_file(file_path, txt):
    with open(file_path, 'w') as file:
        file.write(txt)

def should_ignore(path, ignores):
    """
    Checks if the given path matches any of the ignore patterns.
    
    :param path: The file or directory path to check
    :param ignores: A set of wildcard patterns to ignore (similar to .gitignore)
    :return: True if the path should be ignored, False otherwise
    """
    for pattern in ignores:
        if fnmatch.fnmatch(path, pattern):
            #print( f"Ignoring {path} due to pattern {pattern}" )
            return True
    return False

def find_and_process_files(root_dir, process_file=None, relevant_extensions=None, ignores=[] ):
    """
    Walks through subdirectories of the root_dir, lists files with specified extensions, 
    and runs a user-defined function on them.
    
    :param root_dir: Root directory to start the search from
    :param relevant_extensions: Set of file extensions to include (e.g., {'.h', '.c', '.cpp', '.hpp'})
    """
    flist = []
    if relevant_extensions is None:
        relevant_extensions = {'.h', '.c', '.cpp', '.hpp'}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file_name in filenames:
            full_path = os.path.join(dirpath, file_name)
            if should_ignore(full_path, ignores): continue
            _, ext = os.path.splitext(file_name)
            if ext in relevant_extensions:
                full_path = os.path.join(dirpath, file_name)
                flist.append(full_path)
                if process_file is not None:
                    process_file(full_path)
    return flist

# # Example usage
# if __name__ == '__main__':
#     root_directory = './path_to_your_directory'  # Replace with your directory path
#     find_and_process_files(root_directory)
