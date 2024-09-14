import subprocess
import re




def get_commit_log():
    """Get the git commit log."""
    result = subprocess.run(
        ['git', 'log', '--pretty=format:%H|%an|%ad|%s', '--date=iso'],
        capture_output=True, text=True
    )
    return result.stdout.splitlines()


def get_commit_diff(commit_hash):
    """Get the file name and status for a specific commit."""
    result = subprocess.run(
        ['git', 'show', '--pretty=format:', '--name-status', commit_hash],
        capture_output=True, text=True
    )
    return result.stdout.splitlines()


def get_commit_changes(commit_hash):
    """Get the detailed changes for a specific commit."""
    result = subprocess.run(
        ['git', 'show', commit_hash],
        capture_output=True, text=True
    )
    return result.stdout


def extract_file_changes(file_name, changes):
    """Extract the changes for a specific file in the commit diff."""
    # Regex to capture the changes for the file
    file_diff_pattern = rf'diff --git a/{file_name} b/{file_name}(.*?)diff --git'
    file_diff = re.search(file_diff_pattern, changes, re.DOTALL | re.MULTILINE)

    # Handle the case when the file is the last one in the diff
    if not file_diff:
        file_diff_pattern = rf'diff --git a/{file_name} b/{file_name}(.*)'
        file_diff = re.search(file_diff_pattern, changes, re.DOTALL | re.MULTILINE)

    if file_diff:
        return file_diff.group(1).strip().splitlines()
    
    return []  # Return an empty list if no changes are found


def write_commit_to_markdown(commit_index, commit_data, file_changes, path='./GitCommits/', relevant_extensions=None ):
    """Write the commit details and file changes to a markdown file."""

    if relevant_extensions is None:
        relevant_extensions = {'.h', '.c', '.cpp', '.hpp', '.jl', '.py'}
    
    hash, author, date, message = commit_data
    with open( path + 'commit_%06i.md' %commit_index, 'w') as f:
        f.write(f"# Commit {commit_index}\n\n")
        f.write(f"**Hash**: {hash}\n")
        f.write(f"**Author**: {author}\n")
        f.write(f"**Date**: {date}\n")
        f.write(f"**Message**: {message}\n\n")
        f.write("## Changes:\n\n")

        # Write changes for each file
        for file_name, changes in file_changes.items():

            _, ext = os.path.splitext(file_name)
            if ext in relevant_extensions:
                f.write(f"### File: {file_name}\n")
                f.write("```\n")
                f.write("\n".join(changes))
                f.write("\n```\n\n")


def process_commit(commit_index, commit_line, Ncommits, path='./GitCommits/' ):
    """Process a single commit, extract changes, and write to a markdown file."""
    hash, author, date, message = commit_line.split('|')

    # Get file diffs and actual changes
    file_names = get_commit_diff(hash)
    commit_changes = get_commit_changes(hash)

    # Process changes for each file
    file_changes = {}
    for line in file_names:
        if line:
            parts = line.split('\t', 1)  # Split only on the first tab
            if len(parts) == 2:
                status, file_name = parts
                file_changes[file_name] = extract_file_changes(file_name, commit_changes)

    # Write the commit details and changes to a markdown file
    write_commit_to_markdown( Ncommits-commit_index   , (hash, author, date, message), file_changes, path=path )


def process_all_commits( path = './GitCommits/' ):
    """Main function to process all commits in the repository."""
    commit_log = get_commit_log()
    n = len(commit_log)
    for i, commit_line in enumerate(commit_log, 1):
        process_commit(i, commit_line, n, path=path )
    return n

import os

import os
import fnmatch

def accumulate_files(path, filename_pattern, nmax_char, callback):
    """
    Loops over files matching the user-provided filename pattern in a directory,
    accumulates the content in a single string, and when the string exceeds nmax_char,
    calls the user-provided callback function with the string.
    
    :param directory: Directory where the files are located
    :param filename_pattern: Pattern to match filenames (e.g., "commit_*.md")
    :param nmax_char: Maximum number of characters to accumulate in the string
    :param callback: User-provided function to call when the accumulated string exceeds nmax_char
    """
    accumulated_str = ''
    
    matched_files = sorted(fnmatch.filter(os.listdir(path), filename_pattern))
    i0=0
    i1=0
    for i,file_name in enumerate( matched_files ):
        i1=i
        file_path = os.path.join(path, file_name)
        with open(file_path, 'r') as f: content = f.read()
        if len(accumulated_str) + len(content) > nmax_char:
            #print("acum ", i, i0, i1)
            callback(accumulated_str,(i0+1,i1))
            i0=i1
            accumulated_str = content
        else:
            accumulated_str += content
    if accumulated_str:
        callback(accumulated_str,(i0+1,i1))


# # Example call to the function
# directory = 'path_to_commit_md_files'
# nmax_char = 5000  # Adjust the maximum string length as needed
# accumulate_commits(directory, nmax_char, user_callback)



# if __name__ == '__main__':
#     process_all_commits()
