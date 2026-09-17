import os
import base64
import json

from fastapi import FastAPI, UploadFile, File, HTTPException
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

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "foods": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "grams": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                    "kcal": {"type": "number"}
                },
                "required": [
                    "name",
                    "grams",
                    "carbs_g",
                    "protein_g",
                    "fat_g",
                    "kcal"
                ]
            }
        },
        "carbs_g": {"type": "number"},
        "protein_g": {"type": "number"},
        "fat_g": {"type": "number"},
        "kcal": {"type": "number"},
        "fiber_g": {"type": "number"},
        "sugar_g": {"type": "number"}
    },
    "required": [
        "foods",
        "carbs_g",
        "protein_g",
        "fat_g",
        "kcal",
        "fiber_g",
        "sugar_g"
    ]
}


@app.get("/")
def root():
    return {"status": "NutriFoto API funcionando"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):

    raw = await file.read()

    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Imagen demasiado grande"
        )

    mime = file.content_type or "image/jpeg"

    b64 = base64.b64encode(raw).decode()

    prompt = """
Analiza esta foto de comida.

Identifica cada alimento visible y estima su cantidad en gramos.

Para cada alimento calcula:
- hidratos de carbono
- proteínas
- grasas
- calorías

Calcula también los totales del plato:
- hidratos
- proteínas
- grasas
- calorías
- fibra
- azúcares

Ten en cuenta aceite y salsas visibles.

Redondea los valores.
Una fotografía no permite conocer con precisión el peso,
los ingredientes ni la receta.

No inventes alimentos que no sean razonablemente visibles.
"""

    try:
        response = client.responses.create(
            model="gpt-5.6",
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
                            "image_url": f"data:{mime};base64,{b64}"
                        }
                    ]
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "nutrition",
                    "strict": True,
                    "schema": SCHEMA
                }
            }
        )

        return json.loads(response.output_text)

    except Exception as e:
        print("ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail="Error analizando la imagen"
        )
