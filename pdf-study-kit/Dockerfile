FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pdf_study_kit ./pdf_study_kit
COPY examples ./examples

# APP_MODE=api serves the HTTP API; anything else runs the CLI help.
ENV APP_MODE=api
EXPOSE 8000
CMD ["sh", "-c", "if [ \"$APP_MODE\" = api ]; then python -m uvicorn pdf_study_kit.server:app --host 0.0.0.0 --port 8000; else python -m pdf_study_kit --help; fi"]
