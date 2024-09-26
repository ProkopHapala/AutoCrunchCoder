import os
import fnmatch
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def write_file(file_path, txt, mode='w'):
    with open(file_path, mode) as file:
        file.write(txt)

def save_file_paths(file_list, log_file):
    """
    Function to save PDF paths into a numbered log file
    """
    with open(log_file, "w") as f:
        for i, file_path in enumerate(file_list, 1):
            f.write(f"{i:05d} {file_path}\n")

def load_file_paths(log_file):
    """
    Function to load the saved file paths from log file
    """
    with open(log_file, "r") as f:
        return [(int(line.split()[0]), line.split()[1]) for line in f.readlines()]

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

def find_files(root_dir, process_file=None, relevant_extensions=None, ignores=[], saveToFile=None, bPrint=True, bSort=True ):
    """
    Walks through subdirectories of the root_dir, lists files with specified extensions, 
    and runs a user-defined function on them.
    
    :param root_dir: Root directory to start the search from
    :param relevant_extensions: Set of file extensions to include (e.g., {'.h', '.c', '.cpp', '.hpp'})
    """
    flist = []
    #print(f"find_files: {root_dir}")
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
    if bSort: flist.sort()
    if(bPrint): 
        nfound = len(flist)
        print( f"find_files({root_dir},{relevant_extensions}) found {nfound}" )
    if saveToFile is not None:
        save_file_paths(flist, saveToFile)
    flist = [ (i, file_path) for i, file_path in enumerate(flist, 1) ]
    return flist


def process_files_serial(file_list, process_callback, log_file, output_dir):
    """
    Process files serially using a user-defined callback.
    """
    for i, file_path in file_list:
        try:
            result = process_callback(file_path, output_dir, i)
            if result:
                print(f"Processed {file_path} successfully.")
        except Exception as exc:
            log = f"Error processing {file_path}: {exc}\n"
            print(log)
            with open(log_file, "a") as f:
                f.write(log)

def process_files_parallel(file_list, process_callback, log_file, output_dir, max_workers=4, timeout=60):
    """
    Process files in parallel using threads and a user-defined callback.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_callback, file_path, output_dir, i): (i, file_path) for i, file_path in  file_list   }
        for future in as_completed(futures):
            i, file_path = futures[future]
            try:
                result = future.result(timeout=timeout)
                if result:
                    print(f"Processed {file_path} successfully.")
            except TimeoutError:
                log = f"Timeout reached for {file_path}\n"
                print(log)
                with open(log_file, "a") as f:
                    f.write(log)
            except Exception as exc:
                log = f"Error processing {file_path}: {exc}\n"
                print(log)
                with open(log_file, "a") as f:
                    f.write(log)


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