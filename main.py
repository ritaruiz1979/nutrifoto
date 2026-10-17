import os
import json
import time
import re

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types


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
async def analyze(
    file: UploadFile = File(...),
    peso_total_g: float = Form(None)
):
    try:
        image_bytes = await file.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="La imagen está vacía."
            )

        if peso_total_g is not None and peso_total_g <= 0:
            raise HTTPException(
                status_code=400,
                detail="El peso debe ser mayor que cero."
            )

        mime_type = file.content_type or "image/jpeg"

        prompt = """
Analiza esta foto de comida.

Identifica los alimentos visibles y estima para cada uno:
- nombre
- cantidad_g
- calorias
- proteinas_g
- hidratos_g
- grasas_g

Devuelve exclusivamente un JSON válido con esta estructura:
{
  "alimentos": [
    {
      "nombre": "nombre del alimento",
      "cantidad_g": 100,
      "calorias": 150,
      "proteinas_g": 5,
      "hidratos_g": 20,
      "grasas_g": 4
    }
  ],
  "totales": {
    "calorias": 150,
    "proteinas_g": 5,
    "hidratos_g": 20,
    "grasas_g": 4
  }
}

Los valores son estimaciones nutricionales.
Responde en español.
"""

        if peso_total_g is not None:
            prompt += f"""

El peso TOTAL de la comida es {peso_total_g:.0f} gramos.

Identifica por separado todos los ingredientes visibles,
incluidos los ingredientes principales y el caldo o líquido.

Estima las cantidades individuales procurando que su suma
sea igual al peso total indicado.

No incluyas el peso del plato o recipiente.
Calcula los nutrientes de cada ingrediente según su cantidad
y devuelve los totales correspondientes.
"""

        response = None

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                break

            except Exception as e:
                error_text = str(e).upper()

                es_temporal = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )

                if not es_temporal or attempt == 2:
                    raise

                print(
                    f"REINTENTO AUTOMÁTICO "
                    f"{attempt + 2}/3"
                )

                time.sleep(10 if attempt == 0 else 20)

        if response is None or not response.text:
            raise HTTPException(
                status_code=500,
                detail="Gemini no devolvió una respuesta."
            )

        text = response.text.strip()

        # Limpiar posibles bloques Markdown
        text = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

        try:
            data = json.loads(text)

        except json.JSONDecodeError:
            print("RESPUESTA DE GEMINI:")
            print(text)

            raise HTTPException(
                status_code=500,
                detail="Gemini no devolvió un JSON válido."
            )

        alimentos = data.get("alimentos", [])

        if not isinstance(alimentos, list):
            raise HTTPException(
                status_code=500,
                detail="La lista de alimentos no es válida."
            )

        if peso_total_g is not None and peso_total_g > 0:
            peso_estimado = sum(
                max(0, float(a.get("cantidad_g", 0) or 0))
                for a in alimentos
            )

            if alimentos and peso_estimado > 0:
                factor = peso_total_g / peso_estimado

                for alimento in alimentos:
                    for campo in (
                        "cantidad_g",
                        "calorias",
                        "proteinas_g",
                        "hidratos_g",
                        "grasas_g"
                    ):
                        alimento[campo] = round(
                            float(
                                alimento.get(campo, 0) or 0
                            ) * factor,
                            2
                        )

        # Recalcular los totales a partir de los alimentos
        data["totales"] = {
            campo: round(
                sum(
                    float(a.get(campo, 0) or 0)
                    for a in alimentos
                ),
                2
            )
            for campo in (
                "calorias",
                "proteinas_g",
                "hidratos_g",
                "grasas_g"
            )
        }

        # Mantener el número de reintentos para el historial
        data["reintentos"] = attempt

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
