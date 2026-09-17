import os
import base64

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Falta GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


@app.get("/")
def home():
    return {
        "status": "NutriFoto funcionando",
        "ai": "Gemini"
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "inline_data": {
                        "mime_type": file.content_type,
                        "data": base64.b64encode(image_bytes).decode("utf-8")
                    }
                },
                (
                    "Analiza esta foto de comida. "
                    "Identifica los alimentos visibles y estima para cada uno "
                    "su cantidad aproximada en gramos, calorías, proteínas, "
                    "carbohidratos y grasas. "
                    "Después proporciona el total aproximado. "
                    "Responde en español."
                )
            ]
        )

        return {
            "result": response.text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar la imagen: {str(e)}"
        )










           
