import os,base64,json
from fastapi import FastAPI,UploadFile,File,HTTPException
from openai import OpenAI

app=FastAPI()
client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SCHEMA={
 "type":"object","additionalProperties":False,"properties":{
  "foods":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{
   "name":{"type":"string"},"grams":{"type":"number"},
   "carbs_g":{"type":"number"},"protein_g":{"type":"number"},
   "fat_g":{"type":"number"},"kcal":{"type":"number"}}, "required":["name","grams","carbs_g","protein_g","fat_g","kcal"]}},
  "carbs_g":{"type":"number"},"protein_g":{"type":"number"},"fat_g":{"type":"number"},
  "kcal":{"type":"number"},"fiber_g":{"type":"number"},"sugar_g":{"type":"number"}
 },
 "required":["foods","carbs_g","protein_g","fat_g","kcal","fiber_g","sugar_g"]
}

@app.get("/health")
def health(): return {"ok":True}

@app.post("/analyze")
async def analyze(image:UploadFile=File(...)):
    raw=await image.read()
    if len(raw)>15*1024*1024: raise HTTPException(413,"Imagen demasiado grande")
    mime=image.content_type or "image/jpeg"
    b64=base64.b64encode(raw).decode()
    prompt="""Analiza esta foto de comida. Identifica cada alimento visible y estima su cantidad en gramos.
Calcula hidratos, proteínas, grasas y kcal por alimento y el total del plato. También calcula fibra y azúcares totales.
Ten en cuenta aceite/salsas visibles. Redondea; una foto no permite precisión exacta. No inventes alimentos que no sean razonablemente visibles."""
    r=client.responses.create(
      model="gpt-5.6",
      input=[{"role":"user","content":[
        {"type":"input_text","text":prompt},
        {"type":"input_image","image_url":f"data:{mime};base64,{b64}"}
      ]}],
      text={"format":{"type":"json_schema","name":"nutrition","strict":True,"schema":SCHEMA}}
    )
    return json.loads(r.output_text)
