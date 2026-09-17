import os
import base64
import json
import time

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

        prompt = """
Analiza esta foto de comida.

Identifica los alimentos visibles y estima para cada uno:
- nombre
- cantidad_g
- calorias
- proteinas_g
- hidratos_g
- grasas_g

Después calcula los totales aproximados.

IMPORTANTE:
Responde ÚNICAMENTE con JSON válido, sin Markdown ni texto adicional.

Usa exactamente este formato:

{
  "alimentos": [
    {
      "nombre": "ejemplo",
      "cantidad_g": 100,
      "calorias": 150,
      "proteinas_g": 10,
      "hidratos_g": 20,
      "grasas_g": 5
    }
  ],
  "totales": {
    "calorias": 150,
    "proteinas_g": 10,
    "hidratos_g": 20,
    "grasas_g": 5
  }
}

Todos los valores nutricionales son estimaciones.
Responde en español.
"""

        response = None
        last_error = None

        # Reintentar hasta 3 veces si Gemini está temporalmente saturado
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        {
                            "inline_data": {
                                "mime_type": file.content_type,
                                "data": base64.b64encode(
                                    image_bytes
                                ).decode("utf-8")
                            }
                        },
                        prompt
                    ]
                )

                break

            except Exception as e:
                last_error = e

                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(2 * (attempt + 1))
                    continue

                raise

        if response is None:
            raise last_error

        text = response.text.strip()

        # Eliminar posibles bloques Markdown
        if text.startswith("```json"):
            text = text[7:]

        if text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Gemini no devolvió un JSON válido."
            )

        return data

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar la imagen: {str(e)}"
        )





           
