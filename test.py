from google import genai

# Configure the API key directly for testing purposes
genai.configure(api_key="AIzaSyDwse77rYOuTHYaV10EYkXNhDEmpZ5o0Lk")

response = genai.models.generate_content(
    model="gemini-2.5-flash", contents="Explain how AI works in a few words"
)
print(response.text)