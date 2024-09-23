import os
import fnmatch

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def write_file(file_path, txt):
    with open(file_path, 'w') as file:
        file.write(txt)

def remove_code_block_delimiters(text):
    lines = text.splitlines()
    cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(cleaned_lines)

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
    #print(f"find_and_process_files: {root_dir}")
    if relevant_extensions is None: relevant_extensions = {'.h', '.c', '.cpp', '.hpp'}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file_name in filenames:
            #print(f"Processing file: {file_name}")
            full_path = os.path.join(dirpath, file_name)
            if should_ignore(full_path, ignores): continue
            _, ext = os.path.splitext(file_name)
            if ext in relevant_extensions:
                full_path = os.path.join(dirpath, file_name)
                flist.append(full_path)
                if process_file is not None:
                    process_file(full_path)
    return flist


def accumulate_files_content(file_list, process_function, max_char_limit=65536, nfiles_max=1000000 ):
    """
    Accumulate content from files into a string and process it when the length exceeds max_char_limit.
    
    :param file_list: List of file paths to accumulate content from
    :param max_char_limit: The maximum number of characters allowed before processing the accumulated content
    :param process_function: A user-defined function to call when the accumulated string reaches the limit
    """
    accumulated_parts = []  # List to accumulate parts of the string
    accumulated_length = 0  # Track the current length of the accumulated content
    i0=0
    nfiles=0
    for i,file_path in enumerate(file_list):
        if os.path.isfile(file_path):  # Check if the file exists
            with open(file_path, 'r') as f:
                fnamestr = "# FILE: "+ file_path+"\n\n"
                content = f.read()     # Read the file content
                # If adding this content would exceed the max limit, process the current accumulated string
                dlen = len(fnamestr) + len(content)+2
                nfiles+=1
                if ( accumulated_length + dlen > max_char_limit ) or (nfiles>=nfiles_max):
                    process_function('\n\n'.join(accumulated_parts), (i0,i) )     # Process the current accumulated string
                    # Reset the accumulator
                    accumulated_parts = []
                    accumulated_length = 0
                    i0=i
                    nfiles=0
                # Add the current file content to the accumulator
                accumulated_parts.append(fnamestr)
                accumulated_parts.append(content)
                accumulated_length += dlen
    # Process any remaining accumulated content
    if accumulated_parts:
        process_function('\n\n'.join(accumulated_parts), (i0,i) )



# # Example usage
# if __name__ == '__main__':
#     root_directory = './path_to_your_directory'  # Replace with your directory path
#     find_and_process_files(root_directory)
