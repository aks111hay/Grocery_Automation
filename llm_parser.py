# llm_parser.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
import ast
import re
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_products(user_text):
    prompt = f"""
    Extract a list of grocery product names from this sentence:
    Sentences can be in various formats like:
    - "order milk,kurkure for me"
    - "i want milk kurkure"
    - "I've got your order for Nandani Toned Milk and Maggie"
    - "Thanks! I've got your order for Milk and Bread"
    
    You need to extract only product names and respond in a python list like ["milk","kurkure"]
    "{user_text}"
    Respond in a Python list of strings, no explanation.
    """
    model = genai.GenerativeModel("gemini-2.5-pro")
    response = model.generate_content(prompt)
    
    try:
        # Access the first candidate's text
        text = response.candidates[0].content.parts[0].text
        
        # Extract list from code block
        match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if match:
            return ast.literal_eval(match.group(1))
        
        # Fallback: try to extract plain list even if not in code block
        fallback_match = re.search(r'\[.*?\]', text)
        if fallback_match:
            return ast.literal_eval(fallback_match.group(0))

        return []
    except Exception as e:
        print(f"Error extracting list: {e}")
        return []


if __name__ == "__main__":
    print(extract_products("order milk,kurkure for me"))