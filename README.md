# AutoCrunchCoder
Trying to use various automatic tools and LLMs to speed up development, debugging and optimization of number-crunching code for scientific calculations

## Structure 

* `tests` - containg something like payground for experimenting, testing and examples of different LLM applications and tasks. It is meant for development.
* `scripts` - containin finished scripts for different tasks
* `pyCruncher` - the main python library for automatization of using LLMs for different tasks such as summarization, code generation, etc.

## Installation & Usage

* On Ubuntu linux it is recommended to use python envirnoment which allows to install python packages with `pip`. For exampple
  ```
  alias activate_ml="source ~/venvs/ML/bin/activate"
  activate_ml
  ```
* Then simply navigate to `scripts` or `tests` and run the relevant script 

### Dependencies

Make sure to install all dependencies using `pip install -r requirements.txt`

* Key dependencies are: 
   * `json`
   * `toml`
   * `openai`
* Additional dependencies ( required by some modules) are:
   * `google-generativeai`
   * `tree-sitter`
   * `Maxima`
