
# Help With writing VScode extension
# https://www.perplexity.ai/search/how-to-make-simple-vscode-exte-xO3dy..BT1emdXQGZOtxbw

import sys

# Get the text passed as an argument
if len(sys.argv) > 1:
    input_text = sys.argv[1]
    # Process the input text (for demonstration, we'll just print it)
    print(f"Received text: {input_text}")
else:
    print("No text received.")