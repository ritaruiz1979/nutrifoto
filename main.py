import os
import base64
import json
import time

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

Después calcula los totales aproximados.

Los valores nutricionales son estimaciones basadas en la imagen.

Responde en español.

Si no puedes identificar con certeza un alimento, utiliza la descripción más razonable posible.
"""
        if peso_total_g is not None and peso_total_g > 0:
    prompt += f"""

El usuario indica que el peso TOTAL de la comida del plato es {peso_total_g:.0f} gramos.

Identifica por separado todos los ingredientes visibles, incluyendo el arroz, marisco, otros ingredientes y el caldo o líquido si lo hay.

Estima la cantidad en gramos de cada ingrediente procurando que la suma de todas las cantidades sea igual al peso total indicado de {peso_total_g:.0f} gramos.

No incluyas el peso del plato o recipiente.

Calcula las calorías, proteínas, hidratos y grasas de cada ingrediente según las cantidades estimadas y después calcula los totales.

Los valores nutricionales son aproximados.
"""

        response = None
        last_error = None
        attempt = 0

        for attempt in range(3):

            try:

                response = client.models.generate_content(
                    model="gemini-3.6-flash",

                    contents=[
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(
                                    image_bytes
                                ).decode("utf-8")
                            }
                        },
                        prompt
                    ],

                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "alimentos": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "nombre": {
                                                "type": "string"
                                            },
                                            "cantidad_g": {
                                                "type": "number"
                                            },
                                            "calorias": {
                                                "type": "number"
                                            },
                                            "proteinas_g": {
                                                "type": "number"
                                            },
                                            "hidratos_g": {
                                                "type": "number"
                                            },
                                            "grasas_g": {
                                                "type": "number"
                                            }
                                        },
                                        "required": [
                                            "nombre",
                                            "cantidad_g",
                                            "calorias",
                                            "proteinas_g",
                                            "hidratos_g",
                                            "grasas_g"
                                        ]
                                    }
                                },
                                "totales": {
                                    "type": "object",
                                    "properties": {
                                        "calorias": {
                                            "type": "number"
                                        },
                                        "proteinas_g": {
                                            "type": "number"
                                        },
                                        "hidratos_g": {
                                            "type": "number"
                                        },
                                        "grasas_g": {
                                            "type": "number"
                                        }
                                    },
                                    "required": [
                                        "calorias",
                                        "proteinas_g",
                                        "hidratos_g",
                                        "grasas_g"
                                    ]
                                }
                            },
                            "required": [
                                "alimentos",
                                "totales"
                            ]
                        }
                    )
                )

                break

            except Exception as e:

                last_error = e

                error_text = str(e)

                if (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                ):

                    if attempt == 0:
                        print("REINTENTO AUTOMÁTICO 2/3")
                        time.sleep(10)
                        continue

                    if attempt == 1:
                        print("REINTENTO AUTOMÁTICO 3/3")
                        time.sleep(20)
                        continue

                    raise

                raise


        if response is None:
            raise last_error


        text = response.text.strip()


        try:

            data = json.loads(text)
                    if peso_total_g is not None and peso_total_g > 0:
            alimentos = data.get("alimentos", [])
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
                            float(alimento.get(campo, 0) or 0) * factor,
                            2
                        )

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

        except json.JSONDecodeError:

            print("RESPUESTA DE GEMINI:")
            print(text)

            raise HTTPException(
                status_code=500,
                detail="Gemini no devolvió un JSON válido."
            )


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
    
                                        
