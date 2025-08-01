from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import shutil
import subprocess
from pdf2image import convert_from_path
from PIL import Image

app = FastAPI()

@app.post("/vectorize")
async def vectorize(file: UploadFile = File(...)):
    # 存臨時檔案
    upload_suffix = os.path.splitext(file.filename)[-1].lower()
    input_path = f"/tmp/input{upload_suffix}"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 判斷型別
    if upload_suffix == ".pdf":
        # PDF → PNG
        try:
            pages = convert_from_path(input_path, dpi=300, fmt="png")
        except Exception as e:
            return JSONResponse({"error": f"PDF 轉圖片失敗: {e}"}, status_code=400)
        if not pages:
            return JSONResponse({"error": "PDF 沒有任何頁面"}, status_code=400)
        # 只取第一頁
        img = pages[0]
        png_path = "/tmp/page1.png"
        img.save(png_path)
        img_input_path = png_path
    elif upload_suffix in [".png", ".jpg", ".jpeg"]:
        img_input_path = input_path
    else:
        return JSONResponse({"error": "只接受 PDF, PNG, JPG 檔案"}, status_code=400)

    # 向量化：用 potrace 處理
    # 1. 先轉成黑白 BMP (potrace 支援)
    bw_bmp_path = "/tmp/in.bmp"
    img = Image.open(img_input_path).convert("L").point(lambda x: 0 if x < 128 else 255, '1')
    img.save(bw_bmp_path)

    # 2. 執行 potrace
    svg_output_path = "/tmp/result.svg"
    result = subprocess.run(["potrace", bw_bmp_path, "-s", "-o", svg_output_path])
    if not os.path.exists(svg_output_path):
        return JSONResponse({"error": "potrace 向量化失敗"}, status_code=500)

    return FileResponse(svg_output_path, media_type="image/svg+xml", filename="result.svg")

@app.get("/")
def home():
    return {"msg": "ElmerFEM + SfePy + 圖片/PDF雲端向量化API運作中"}
