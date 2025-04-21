#!/usr/bin/env python3

"""
Example demonstrating batch PDF processing and summarization using parallel execution.
This example shows how to:
1. Process multiple PDFs in parallel using ThreadPoolExecutor
2. Extract text from PDFs using pdfminer.six
3. Generate summaries using LLMs
4. Handle timeouts and errors gracefully
5. Log processing results

Requirements:
    pip install pdfminer.six
"""

import os
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pdfminer.high_level import extract_text
from pyCruncher2.agents.openai import AgentOpenAI
from pyCruncher2.utils.files import find_files, write_file, read_file

@dataclass
class BatchConfig:
    """Configuration for batch PDF processing."""
    input_dir: str
    output_dir: str
    max_workers: int = 4
    timeout_seconds: int = 60
    max_chars: int = 300000
    model_name: str = "fzu-llama-8b"
    file_extensions: set = frozenset({'.pdf'})

def setup_directories(config: BatchConfig) -> None:
    """Create output directories if they don't exist."""
    os.makedirs(config.output_dir, exist_ok=True)
    
    # Create subdirectories for different stages
    for subdir in ['extracted_text', 'summaries', 'logs']:
        os.makedirs(os.path.join(config.output_dir, subdir), exist_ok=True)

def process_pdf(
    pdf_path: str,
    output_dir: str,
    pdf_num: int
) -> Optional[Tuple[str, int]]:
    """
    Process a single PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted text
        pdf_num: Unique number for the PDF
        
    Returns:
        Optional[Tuple[str, int]]: Output name and character count if successful
    """
    output_name = f"PDF_{pdf_num:05d}"
    output_file = os.path.join(output_dir, 'extracted_text', output_name + '.md')
    log_file = os.path.join(output_dir, 'logs', 'extraction.log')

    # Skip if already processed
    if os.path.exists(output_file):
        print(f"Skipping {pdf_path} (already processed)")
        return None

    try:
        # Extract and save text
        pdf_text = extract_text(pdf_path)
        char_count = len(pdf_text)
        
        # Log success
        log_entry = f"{output_name} {char_count:<7} {pdf_path}\n"
        print(log_entry.strip())
        write_file(log_file, log_entry, mode="a")
        
        # Save extracted text
        write_file(output_file, pdf_text)
        return output_name, char_count
        
    except Exception as e:
        # Log error
        log_entry = f"Error processing {pdf_path}: {str(e)}\n"
        print(log_entry.strip())
        write_file(log_file, log_entry, mode="a")
        return None

def process_pdfs_parallel(config: BatchConfig) -> None:
    """
    Process multiple PDFs in parallel with timeout handling.
    
    Args:
        config: Batch processing configuration
    """
    # Find all PDF files
    pdf_files = find_files(config.input_dir, relevant_extensions=config.file_extensions)
    if not pdf_files:
        print(f"No PDF files found in {config.input_dir}")
        return
    
    # Create file number mapping
    file_numbers = {pdf_file: i + 1 for i, pdf_file in enumerate(pdf_files)}
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_pdf,
                pdf_file,
                config.output_dir,
                file_numbers[pdf_file]
            ): pdf_file for pdf_file in pdf_files
        }
        
        # Handle completions and timeouts
        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                result = future.result(timeout=config.timeout_seconds)
                if result:
                    print(f"Successfully processed {pdf_file}")
            except TimeoutError:
                log_entry = f"Timeout reached for {pdf_file}\n"
                print(log_entry.strip())
                write_file(
                    os.path.join(config.output_dir, 'logs', 'timeouts.log'),
                    log_entry,
                    mode="a"
                )
            except Exception as e:
                log_entry = f"Error processing {pdf_file}: {str(e)}\n"
                print(log_entry.strip())
                write_file(
                    os.path.join(config.output_dir, 'logs', 'errors.log'),
                    log_entry,
                    mode="a"
                )

def summarize_text(
    text: str,
    agent: AgentOpenAI,
    max_chars: int,
    stream: bool = True
) -> Optional[str]:
    """
    Generate a summary of the text using an LLM.
    
    Args:
        text: Text to summarize
        agent: LLM agent
        max_chars: Maximum allowed characters
        stream: Whether to stream the output
        
    Returns:
        Optional[str]: Generated summary if successful
    """
    if len(text) >= max_chars:
        return None
        
    if stream:
        for chunk in agent.stream(text):
            print(chunk, flush=True, end="")
        return agent.assistant_message
    else:
        response = agent.query(text)
        return response.text

def process_summaries(config: BatchConfig) -> None:
    """
    Generate summaries for all extracted text files.
    
    Args:
        config: Batch processing configuration
    """
    # Initialize LLM agent
    agent = AgentOpenAI(config.model_name)
    
    # Find all extracted text files
    text_dir = os.path.join(config.output_dir, 'extracted_text')
    md_files = find_files(text_dir, relevant_extensions={'.md'})
    
    for md_file in md_files:
        print(f"Processing {md_file}")
        
        # Read extracted text
        text = read_file(md_file)
        
        # Generate and save summary
        summary = summarize_text(text, agent, config.max_chars)
        if summary:
            output_file = os.path.join(
                config.output_dir,
                'summaries',
                os.path.basename(md_file)
            )
            write_file(output_file, summary)
        else:
            log_entry = f"Text too long for {md_file}\n"
            print(log_entry.strip())
            write_file(
                os.path.join(config.output_dir, 'logs', 'summary_errors.log'),
                log_entry,
                mode="a"
            )

def main():
    # Example configuration
    config = BatchConfig(
        input_dir='/home/prokophapala/Desktop/PAPERs/',
        output_dir='/home/prokophapala/Desktop/PAPERs_meta/',
        max_workers=4,
        timeout_seconds=60,
        max_chars=300000,
        model_name="fzu-llama-8b"
    )
    
    try:
        # Create directory structure
        setup_directories(config)
        
        # Extract text from PDFs
        print("\n=== Extracting Text from PDFs ===")
        process_pdfs_parallel(config)
        
        # Generate summaries
        print("\n=== Generating Summaries ===")
        process_summaries(config)
        
        print("\nProcessing completed successfully!")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")

if __name__ == "__main__":
    main()
