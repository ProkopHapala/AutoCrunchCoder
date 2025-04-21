#!/usr/bin/env python3

"""
Example demonstrating source code analysis and summarization using LLMs.
This example shows how to:
1. Process and analyze C/C++ source files
2. Generate structured summaries using LLMs
3. Handle large files and character limits
4. Track skipped files and process them separately
5. Support multiple LLM providers (OpenAI, DeepSeek)

Requirements:
    pip install langchain
"""

import os
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, field
from pyCruncher2.agents.openai import AgentOpenAI
from pyCruncher2.agents.deepseek import AgentDeepSeek
from pyCruncher2.utils.files import find_files

@dataclass
class SummarizationConfig:
    """Configuration for code summarization."""
    input_dir: str
    output_dir: str
    model_name: str = "fzu-Qwen25-32b"
    max_chars: int = 32768
    file_extensions: set = field(default_factory=lambda: {'.h', '.c', '.cpp', '.hpp'})
    ignore_patterns: set = field(default_factory=lambda: {'*/Build*', '*/doxygen'})
    system_prompt: str = """
You are helpful assistant and a senior programmer of physical simulations and computational chemistry.
"""
    analysis_prompt: str = """
You are given a C/C++ source code which you should analyze and summarize into markdown file.
First try to understand the code and the overall purpose of the module, class or program implemented in the file. What is the role of this file in the project?
Then identify all global or class-level variables and identify their purpose.
List those variables and write one line for each of them.
Then identify all functions and methods and their purpose.
List those functions and methods and write one line for each of them.
Write everything in concise structured way, using bullet points.
You may assume that the code focus mostly on physical/chemical simulations and applied mathematics. Therefore assume terminology and abbreviations which are appropriate for this domains.
For example:
* `E`,`F`,`v` are probably energy, force and velocity.
* `r` and `l` are radius. `T` is temperature or time.
* `d` is probably difference or derivative.
* `L-J` is probably Lennard-Jones potential.

Please analyze the following code:
"""

def setup_directories(config: SummarizationConfig) -> None:
    """Create output directories if they don't exist."""
    os.makedirs(config.output_dir, exist_ok=True)

def process_file(
    file_path: str,
    agent: AgentOpenAI,
    config: SummarizationConfig,
    log_file: str
) -> bool:
    """
    Process a single source code file.
    
    Args:
        file_path: Path to the source file
        agent: LLM agent for summarization
        config: Summarization configuration
        log_file: Path to the log file for skipped files
        
    Returns:
        bool: True if file was processed successfully
    """
    # Check file size
    file_size = os.path.getsize(file_path)
    prompt_size = len(config.system_prompt) + len(config.analysis_prompt)
    
    if (file_size + prompt_size) > config.max_chars:
        log_entry = f"Skipping {file_path}, file is too large ({file_size} bytes).\n"
        print(log_entry.strip())
        with open(log_file, 'a') as f:
            f.write(log_entry)
        return False
    
    try:
        # Read and process file
        with open(file_path, 'r') as f:
            content = f.read()
        
        task = config.analysis_prompt + "\n\n" + content
        total_len = len(task) + len(config.system_prompt) + 2
        
        if total_len < config.max_chars:
            print(f"Processing {file_path}")
            response = agent.query(task)
            
            # Save summary
            output_file = os.path.join(
                config.output_dir,
                os.path.basename(file_path) + '.md'
            )
            with open(output_file, 'w') as f:
                f.write(response.text)
            return True
            
        else:
            log_entry = f"File {file_path} exceeds character limit (length: {len(content)} chars).\n"
            print(log_entry.strip())
            with open(log_file, 'a') as f:
                f.write(log_entry)
            return False
            
    except Exception as e:
        log_entry = f"Error processing {file_path}: {str(e)}\n"
        print(log_entry.strip())
        with open(log_file, 'a') as f:
            f.write(log_entry)
        return False

def clean_skipped_log(
    input_log: str,
    output_log: str,
    base_path: str
) -> List[Tuple[str, int]]:
    """
    Clean and sort the skipped files log.
    
    Args:
        input_log: Path to input log file
        output_log: Path to output log file
        base_path: Base path to remove from file paths
        
    Returns:
        List[Tuple[str, int]]: Sorted list of (file_path, size) tuples
    """
    base_len = len(base_path)
    file_sizes: Dict[str, int] = {}
    
    # Parse input log
    with open(input_log, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4:
                fname = parts[1][base_len:-1]
                size = int(parts[-2][1:])
                file_sizes[fname] = size
    
    # Sort by size
    sorted_files = sorted(
        file_sizes.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Write cleaned log
    with open(output_log, 'w') as f:
        for fname, size in sorted_files:
            f.write(f"{fname:<100} {size}\n")
    
    return sorted_files

def process_large_files(
    file_list: List[Tuple[str, int]],
    config: SummarizationConfig
) -> None:
    """
    Process files that were previously skipped due to size.
    
    Args:
        file_list: List of (file_path, size) tuples
        config: Summarization configuration
    """
    agent = AgentDeepSeek()
    
    for fname, size in file_list:
        filepath = os.path.join(config.input_dir, fname)
        print(f"\n=== Processing {filepath} ({size} bytes) ===\n")
        
        try:
            # Read file
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Generate summary
            task = config.analysis_prompt + "\n\n" + content
            response = agent.query(task)
            
            # Save summary
            output_file = os.path.join(
                config.output_dir,
                os.path.basename(filepath) + '.md'
            )
            with open(output_file, 'w') as f:
                f.write(response.content)
            print(f"Summary saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing {filepath}: {str(e)}")

def main():
    # Example configuration
    config = SummarizationConfig(
        input_dir="/home/prokop/git/FireCore/cpp/",
        output_dir="./cpp_summaries_FireCore/",
        model_name="fzu-Qwen25-32b",
        max_chars=32768
    )
    
    try:
        # Create output directory
        setup_directories(config)
        
        # Initialize agent
        agent = AgentOpenAI(config.model_name)
        agent.set_system_prompt(config.system_prompt)
        
        # Process files
        print("\n=== Processing Source Files ===")
        log_file = os.path.join(config.output_dir, 'skipped.log')
        find_files(
            config.input_dir,
            process_file=lambda f: process_file(f, agent, config, log_file),
            relevant_extensions=config.file_extensions,
            ignores=config.ignore_patterns
        )
        
        # Clean and sort skipped files
        print("\n=== Processing Large Files ===")
        sorted_files = clean_skipped_log(
            os.path.join(config.output_dir, 'skipped.log'),
            os.path.join(config.output_dir, 'skipped_clean.log'),
            config.input_dir
        )
        
        # Process large files with DeepSeek
        process_large_files(sorted_files, config)
        
        print("\nProcessing completed successfully!")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")

if __name__ == "__main__":
    main()
