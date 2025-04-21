#!/usr/bin/env python3

"""
Example demonstrating BibTeX processing and paper classification using LLMs.
This example shows how to:
1. Load and parse BibTeX files
2. Extract abstracts and titles
3. Classify papers using LLMs
4. Generate research area keywords
5. Batch process large libraries

Requirements:
    pip install langchain bibtexparser
"""

import os
from typing import Optional, Dict, List, Callable, TextIO
from dataclasses import dataclass, field
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from pyCruncher2.agents.openai import AgentOpenAI
from pyCruncher2.agents.deepseek import AgentDeepSeek

@dataclass
class ClassificationConfig:
    """Configuration for paper classification."""
    input_file: str
    output_file: str
    model_name: str = "meta-llama/Llama-2-7b-chat-hf"
    max_papers: int = 100000
    system_prompt: str = """
Please classify the following research article based on its title and abstract.
Define 10 keywords specifying the research topic. Prefer specific narrow domains 
(like "DNA origami", "Gaussian basis set", "Electron force-field") over broad (like "physics").

Your response should be in the following format:
Keywords:
1. [specific keyword 1]
2. [specific keyword 2]
...
10. [specific keyword 10]

Research Areas:
- [primary research area]
- [secondary research area]
- [tertiary research area]

Brief Summary:
[2-3 sentences summarizing the key focus and contribution]
"""

def setup_output_file(config: ClassificationConfig) -> TextIO:
    """Create and initialize the output file."""
    os.makedirs(os.path.dirname(config.output_file), exist_ok=True)
    return open(config.output_file, "w", encoding="utf-8")

def process_entry(
    entry: Dict[str, str],
    agent: AgentOpenAI,
    output_file: TextIO
) -> None:
    """
    Process a single BibTeX entry.
    
    Args:
        entry: BibTeX entry dictionary
        agent: LLM agent for classification
        output_file: Output file handle
    """
    # Extract paper info
    title = entry.get('title', '')
    abstract = entry.get('abstract', '')
    authors = entry.get('author', '')
    year = entry.get('year', '')
    
    if not title or not abstract:
        return
    
    # Format paper info
    paper_info = f"""
Title: {title}
Authors: {authors}
Year: {year}

Abstract:
{abstract}
"""
    
    try:
        # Get classification from LLM
        response = agent.query(paper_info)
        
        # Write to output file
        output_file.write("\n" + "="*80 + "\n")
        output_file.write(paper_info)
        output_file.write("\nClassification:\n")
        output_file.write(response.text)
        output_file.write("\n")
        output_file.flush()
        
    except Exception as e:
        print(f"Error processing entry '{title}': {str(e)}")

def process_bibtex_file(config: ClassificationConfig) -> None:
    """
    Process a BibTeX file and classify papers.
    
    Args:
        config: Classification configuration
    """
    try:
        # Initialize LLM agent
        agent = AgentOpenAI(config.model_name)
        agent.set_system_prompt(config.system_prompt)
        
        # Setup parser
        parser = BibTexParser()
        parser.customization = convert_to_unicode
        
        # Open output file
        with open(config.output_file, "w", encoding="utf-8") as output_file:
            # Write header
            output_file.write("# Paper Classifications\n\n")
            output_file.write(f"BibTeX file: {config.input_file}\n")
            output_file.write(f"Model: {config.model_name}\n\n")
            
            # Process entries
            print(f"Loading BibTeX file: {config.input_file}")
            with open(config.input_file, encoding="utf-8") as bibtex_file:
                bib_database = bibtexparser.load(bibtex_file, parser=parser)
            
            total_entries = len(bib_database.entries)
            print(f"Found {total_entries} entries")
            
            for i, entry in enumerate(bib_database.entries[:config.max_papers], 1):
                print(f"Processing entry {i}/{total_entries}")
                process_entry(entry, agent, output_file)
        
        print("\nProcessing completed successfully!")
        print(f"Results saved to: {config.output_file}")
        
    except Exception as e:
        print(f"Error processing BibTeX file: {str(e)}")

def main():
    # Example configuration
    config = ClassificationConfig(
        input_file="/home/prokophapala/Documents/Mendeley Desktop/library.bib",
        output_file="./paper_classifications.md",
        model_name="meta-llama/Llama-2-7b-chat-hf",
        max_papers=100000
    )
    
    # Process BibTeX file
    process_bibtex_file(config)

if __name__ == "__main__":
    main()
