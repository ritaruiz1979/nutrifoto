import os
import json
import base64
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("Falta la variable OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


@app.get("/")
def home():
    return {"status": "NutriFoto API funcionando"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="La imagen está vacía"
        )

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Analiza esta fotografía de comida para NutriFoto.

Identifica los alimentos visibles y estima la cantidad aproximada de cada uno.

Devuelve ÚNICAMENTE JSON válido, sin markdown ni texto adicional.

La estructura debe ser exactamente:

{
  "alimentos": [
    {
      "nombre": "nombre del alimento",
      "cantidad_g": 0,
      "hidratos_g": 0,
      "calorias": 0,
      "proteinas_g": 0,
      "grasas_g": 0,
      "fibra_g": 0,
      "azucares_g": 0
    }
  ],
  "totales": {
    "hidratos_g": 0,
    "calorias": 0,
    "proteinas_g": 0,
    "grasas_g": 0,
    "fibra_g": 0,
    "azucares_g": 0
  },
  "confianza": 0,
  "observaciones": ""
}

Las cantidades son estimaciones basadas únicamente en la fotografía.
Si un alimento o cantidad no puede determinarse con seguridad,
indícalo en "observaciones".
"""

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{file.content_type};base64,{image_base64}"
                        }
                    ]
                }
            ]
        )

        text = response.output_text.strip()

        # Por si la IA devuelve el JSON dentro de ```json ... ```
        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "")
            text = text.strip()

        result = json.loads(text)

        return result
                except 
        json.JSONDecodeError:
                    raise 
        HTTPException(
        status_code=500,
                        detail="La IA 
        no devolvió un resultado JSON 
        válido"
                    )

           except Exception as e:
               import traceback
               traceback.print_exc()
               raise HTTPException(
                   status_code=500,
                   detail=f"ERROR 
        REAL OPENAI: 
        {type(e).__name__}: {str(e)}"
                )
