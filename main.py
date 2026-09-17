import os
import json
import base64

from fastapi import FastAPI, 
File, UploadFile, 
HTTPException
from fastapi.middleware.cors 
import CORSMiddleware

from google import genai
from google.genai import 
types


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_key = 
os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Falta 
    la variable GEMINI_API_KEY")


client = 
genai.Client(api_key=api_key)


@app.get("/")
def home():
    return {"status":    
"NutriFoto API funcionando"}


@app.post("/analyze")
async def analyze(file: 
UploadFile = File(...)):

    if not file.content_type 
or not 
file.content_type.startswith(   
"image/"):
        raise HTTPException(
            status_code=400,
            detail="El 
 archivo deber ser una imagen"
         )

     image_bytes = await
 file.read()

     if not image_bytes:
         raise HTTPException(
             status_code=400,
             detail="La imagen 
 está vacía"
             )

    prompt = """
Analiza esta fotografía
de comida para NutriFoto.

Identifica los alimentos
visibles y estima la cantidad
aproximada de cada uno.

Devuelve ÚNICAMENTE un objeto
JSON válido.

La estructura debe ser 
exactamente:

{
  "alimentos": [
    {
      "nombre": "nombre del
      alimento",
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

Las cantidades son 
estimaciones basadas
únicamente en la fotografía.

Si un alimento o cantidad no
puede determinarse con 
seguridad,
indícalo en "observaciones".
"""

    try:
        response = 
client.models.generate_conten
t(
model="gemini-3.8-flash",
            contents=[
types.Part.from_text(text=pro
mpt),
types.Part.from_bytes(
data=image_bytes,
mime_type=file.content_type
                 )
            ],
config=types.GenerateContentC
onfig(
response_mime_type="applicati
on/json",
temperature=0.2
            )
        )

        text = 
response.text.strip()

        result = 
json.loads(text)

        return result

     except 
json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Gemini no 
devolvió un resultado JSON 
válido"
        )

       except Exception as e:
           import traceback
           traceback.print_exc()
   
        raise HTTPException(
            status_code=500,
            detail=f"ERROR 
REAL GEMINI: 
{type(e).__name__}: {str(e)}"
        )
