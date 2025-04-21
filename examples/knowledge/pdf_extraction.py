#!/usr/bin/env python3

"""
Example demonstrating PDF text extraction and summarization using pdfminer.six and LLMs.
This example shows how to:
1. Extract text from PDF files using pdfminer.six
2. Create structured prompts for research paper analysis
3. Generate comprehensive summaries using LLMs
4. Handle streaming responses for real-time output

Requirements:
    pip install pdfminer.six
"""

import os
from typing import Optional, Generator, Union
from dataclasses import dataclass, field
from pdfminer.high_level import extract_text
from pyCruncher2.agents.base import AgentResponse
from pyCruncher2.agents.openai import AgentOpenAI

@dataclass
class SummarizationConfig:
    """Configuration for PDF summarization."""
    max_chars: int = 300000
    stream_output: bool = True
    model_name: str = "fzu-llama-8b"
    input_file: str = "debug/pdf_input.md"
    output_file: str = "debug/pdf_output.md"
    prompt_template: str = field(default="""
Please summarize the following research article.  
The text was extracted from a PDF and may contain irrelevant characters or formatting errors, which can be ignored.

### Instructions:

1. **Section Identification**: Identify and segment the following sections, if present:
   - Title
   - Abstract
   - Introduction
   - Results
   - Discussion
   - Conclusions

2. **Core Extraction**:
   - Extract the **main message** of the paper.
   - Identify the **motivation** and **goals** of the research.
   - Highlight the **results** and what was achieved.

3. **Categorization**:
   - Classify the article into **narrow, specific domains**. Avoid broad categories like "physics" or "chemistry." 
   - Instead, use precise topics such as "hydrogen bonding," "local basis sets," "quaternions," "post-Hartree-Fock methods," "density functional theory," "graphene," "DNA origami," etc.

4. **Formulas, Methods, and Abbreviations**:
   - If the article contains any key equations, rewrite them in LaTeX.
   - List any computational or experimental methods, as well as abbreviations mentioned, such as B3LYP, pVDZ, FFT, AFM, DFT, etc.

5. **Format**: Present the summary in the following structure:
   1. **Title**
   2. **Keywords** (specific research domains)
   3. **Essence** (Main message)
   4. **Motivation** (Goals)
   5. **Results** (What was achieved)
   6. **Key Equations** (in LaTeX, if applicable)
   7. **Methods and Abbreviations**

**Conciseness and Focus**:
   - Keep the summary concise and structured, with a maximum length of one A4 page.
   - Focus on the **main findings**, avoiding excessive details or filler text.

The raw text extracted from the article follows below:  
----------------------
""")

def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    return extract_text(pdf_path)

def create_summary_prompt(text: str, template: str) -> str:
    """
    Create a summarization prompt by combining template and text.
    
    Args:
        text: Text to summarize
        template: Prompt template
        
    Returns:
        str: Complete prompt for the LLM
    """
    return template + text

def save_to_file(content: str, filepath: str) -> None:
    """Save content to a file, creating directories if needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)

def summarize_pdf(
    pdf_path: str,
    config: SummarizationConfig
) -> Union[str, Generator]:
    """
    Extract and summarize text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        config: Summarization configuration
        
    Returns:
        Union[str, Generator]: Summary text or stream of tokens
    """
    # Extract text from PDF
    pdf_text = extract_pdf_text(pdf_path)
    
    # Create and validate prompt
    prompt = create_summary_prompt(pdf_text, config.prompt_template)
    if len(prompt) >= config.max_chars:
        raise ValueError(
            f"Input text too long: {len(prompt)} chars (max {config.max_chars})"
        )
    
    # Save input for debugging
    save_to_file(prompt, config.input_file)
    print(f"Processing PDF: {pdf_path}")
    print(f"Character count: {len(prompt)}")
    
    # Initialize agent and generate summary
    agent = AgentOpenAI(config.model_name)
    
    if config.stream_output:
        # Stream response in real-time
        response_stream = agent.stream(prompt)
        for chunk in response_stream:
            print(chunk, flush=True, end="")
        response = agent.assistant_message
    else:
        # Get complete response
        response = agent.query(prompt).text
        print(response)
    
    # Save output for debugging
    save_to_file(response, config.output_file)
    return response

def main():
    # Example configuration
    config = SummarizationConfig(
        max_chars=300000,
        stream_output=True,
        model_name="fzu-llama-8b",
        input_file="debug/pdf_input.md",
        output_file="debug/pdf_output.md"
    )
    
    # Example PDF path
    pdf_path = "/home/prokophapala/Desktop/PAPERs/Elner_triazine_PhysRevB.96.075418.pdf"
    
    try:
        # Generate summary
        summary = summarize_pdf(pdf_path, config)
        print("\nSummary generated successfully!")
        
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
