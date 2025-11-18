# To list available models for Gemini API

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def list_available_models():
    """List all available Gemini models"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_actual_api_key_here':
        print("❌ Please set your actual Gemini API key in the .env file")
        return
    
    try:
        genai.configure(api_key=api_key)
        
        # List all available models
        models = genai.list_models()
        
        print("✅ Available Gemini Models:")
        print("-" * 50)
        
        for model in models:
            if 'gemini' in model.name.lower():
                print(f"📌 Name: {model.name}")
                print(f"   Display Name: {model.display_name}")
                print(f"   Description: {model.description}")
                print(f"   Supported Generation Methods: {model.supported_generation_methods}")
                print("-" * 30)
                
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")

if __name__ == "__main__":
    list_available_models()