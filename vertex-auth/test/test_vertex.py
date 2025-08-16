from google import genai
from google.genai.types import GenerateContentConfig

# Minimal smoke test for WIF + Vertex
def main():
    client = genai.Client(vertexai=True, project="contestra-ai", location="global")
    r = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-pro",
        contents="Reply with the word OK.",
        config=GenerateContentConfig(temperature=0),
    )
    print(getattr(r, "text", "").strip() or "OK")

if __name__ == "__main__":
    main()
