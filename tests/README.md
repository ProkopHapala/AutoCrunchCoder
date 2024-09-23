# pyCruncher Tests

This directory contains test files for the pyCruncher project, including tests for various AI agents such as Google AI and DeepSeek.

## Setup

Before running the tests, make sure you have:

1. Installed all required dependencies:
   ```
   pip install -r ../requirements.txt
   ```

2. Set up your API keys:
   - Create a file named `providers.key` in this directory
   - Add your API keys to this file in the following format:
     ```
     [api_keys]
     google = "your_google_api_key_here"
     deepseek = "your_deepseek_api_key_here"
     # Add other provider keys as needed
     ```

## Running Tests

To run a specific test file, use the following command:

```
python -m unittest test_file_name.py
```

For example, to run the Google AI tests:

```
python -m unittest test_GoogleAI.py
```

To run all tests in this directory:

```
python -m unittest discover
```

## Test Files

- `test_GoogleAI.py`: Tests for the Google AI agent
- `test_DeepSeek_Tools.py`: Tests for the DeepSeek agent and tools
- (Add descriptions for other test files as they are created)

## Note on API Usage

These tests interact with various AI APIs and may incur costs. Make sure you understand the pricing and usage limits of your API keys before running these tests. It's recommended to monitor your usage and set up billing alerts to avoid unexpected charges.

## Contributing

When adding new tests or modifying existing ones, please ensure that:

1. All tests are properly documented with clear docstrings
2. Any new dependencies are added to the project's `requirements.txt` file
3. This README is updated to reflect any new test files or setup requirements