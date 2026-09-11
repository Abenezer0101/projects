"""FastAPI server.  python -m pdf_study_kit.server  ->  http://localhost:8000/docs"""
from __future__ import annotations
import tempfile, pathlib

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse

from . import __version__
from .extract import extract, ExtractionError
from .generate import build, FORMATS

app = FastAPI(title="PDF Study Kit", version=__version__,
              description="Turn a PDF into study material. No external services.")

MAX_BYTES = 25 * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "formats": list(FORMATS)}


@app.post("/generate", response_class=PlainTextResponse)
async def generate(file: UploadFile = File(...),
                   format: str = Query("all", enum=list(FORMATS))):
    payload = await file.read()
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, f"file exceeds {MAX_BYTES // 1024 // 1024} MB")
    if not payload:
        raise HTTPException(400, "empty upload")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
        fh.write(payload); tmp = fh.name
    try:
        doc = extract(tmp, display_name=file.filename or "upload.pdf")
        return build(doc, format)
    except ExtractionError as e:
        raise HTTPException(422, str(e))
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def run():                                             # pragma: no cover
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":                             # pragma: no cover
    run()
