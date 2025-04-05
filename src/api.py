import os
import time
import json
import base64
from os.path import isfile, join, basename, dirname, normpath
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from starlette.responses import PlainTextResponse, HTMLResponse


# API models
class TranscriptionStatus(BaseModel):
    file_name: str
    status: str
    progress: float
    estimated_time_left: int = 0
    error_message: Optional[str] = None

class TranscriptionResponse(BaseModel):
    job_id: str
    message: str

# API functions
def get_api_router():
    from fastapi import APIRouter
    router = APIRouter(prefix="/api", tags=["API"])
    
    @router.post("/transcribe", response_model=TranscriptionResponse)
    async def transcribe_file(
        file: UploadFile = File(...),
        hotwords: Optional[str] = Form(None),
        api_key: Optional[str] = Form(None),
    ):
        """
        Upload files for transcription
        """
        from main import ROOT, handle_upload_api
        
        # Validate API key if configured
        api_key_env = os.getenv("API_KEY")
        if api_key_env and api_key != api_key_env:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Generate a unique user ID based on file content hash with STORAGE_SECRET as salt
        import hashlib

        # Get STORAGE_SECRET from environment variables
        storage_secret = os.getenv("STORAGE_SECRET", "default_salt")
        
        # Create a hash of all file contents with STORAGE_SECRET as salt, so that we don't need to process the same files twice
        hasher = hashlib.sha256()
        hasher.update(storage_secret.encode())

        # Add content of each file to the hash
        content = file.file.read()
        hasher.update(content)
        # Reset file position for later reading
        file.file.seek(0)

        file_api_id = f"api_{hasher.hexdigest()}"
        
        # Create user directories
        in_path = join(ROOT, "data", "in", file_api_id)
        os.makedirs(in_path, exist_ok=True)
        
        # Save hotwords if provided
        if hotwords:
            hotwords_file = join(in_path, "hotwords.txt")
            with open(hotwords_file, "w") as f:
                f.write(hotwords)
        
        # Process file
        file_name = file.filename
        file_content = await file.read()

        # Save the file
        with open(join(in_path, file_name), "wb") as f:
            f.write(file_content)

        return TranscriptionResponse(
            job_id=file_api_id,
            message=f"Files uploaded successfully. Use GET /api/status/{file_api_id} to check status."
        )
    
    @router.get("/status/{job_id}", response_model=TranscriptionStatus)
    async def get_status(job_id: str):
        """
        Get the status of transcription jobs
        """
        from main import ROOT
        
        # Validate job ID format
        if not job_id.startswith("api_"):
            raise HTTPException(status_code=400, detail="Invalid job ID format")
        
        # Check if job exists
        in_path = join(ROOT, "data", "in", job_id)
        out_path = join(ROOT, "data", "out", job_id)
        error_path = join(ROOT, "data", "error", job_id)
        worker_path = join(ROOT, "data", "worker", job_id)
        
        if not (os.path.exists(in_path) or os.path.exists(out_path) or os.path.exists(error_path)):
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check files in queue
        
        # Find the single file in the directory
        if os.path.exists(in_path):
            for f in os.listdir(in_path):
                if isfile(join(in_path, f)) and f != "hotwords.txt":
                    # Check if file is completed
                    if os.path.exists(out_path) and isfile(join(out_path, f + ".html")):
                        return TranscriptionStatus(
                            file_name=f,
                            status="completed",
                            progress=100.0
                        )
                    # Check if file is being processed
                    elif os.path.exists(worker_path):
                        for worker_file in os.listdir(worker_path):
                            if isfile(join(worker_path, worker_file)):
                                parts = worker_file.split("_")
                                if len(parts) < 3:
                                    continue
                                worker_filename = "_".join(parts[2:])
                                if worker_filename == f:
                                    estimated_time = float(parts[0])
                                    start = float(parts[1])
                                    progress = min(0.975, (time.time() - start) / estimated_time)
                                    estimated_time_left = round(max(1, estimated_time - (time.time() - start)))
                                    
                                    return TranscriptionStatus(
                                        file_name=f,
                                        status="processing",
                                        progress=progress * 100,
                                        estimated_time_left=estimated_time_left
                                    )
                        
                        # If we didn't find the file in worker directory, it's queued
                        return TranscriptionStatus(
                            file_name=f,
                            status="queued",
                            progress=0.0
                        )
                    else:
                        return TranscriptionStatus(
                            file_name=f,
                            status="queued",
                            progress=0.0
                        )
        
        # Check error files
        if os.path.exists(error_path):
            for f in os.listdir(error_path):
                if isfile(join(error_path, f)) and not f.endswith(".txt"):
                    error_message = "Transcription failed"
                    error_file = join(error_path, f + ".txt")
                    if isfile(error_file):
                        with open(error_file, "r") as txtf:
                            content = txtf.read()
                            if content:
                                error_message = content
                    
                    return TranscriptionStatus(
                        file_name=f,
                        status="error",
                        progress=-1.0,
                        error_message=error_message
                    )
        
        # If we got here and didn't find any files, return a generic status
        raise HTTPException(status_code=404, detail="No files found for this job")
    @router.get("/download/{job_id}/{file_name}")
    async def download_file(job_id: str, file_name: str, format: str = "html"):
        """
        Download a transcribed file (HTML, SRT, or TXT)
        """
        from main import ROOT
        
        # Validate job ID format
        if not job_id.startswith("api_"):
            raise HTTPException(status_code=400, detail="Invalid job ID format")
        
        out_path = join(ROOT, "data", "out", job_id)
        if not os.path.exists(out_path):
            raise HTTPException(status_code=404, detail="Job not found")

        # Determine file type from extension or format parameter
        file_ext = os.path.splitext(file_name)[1].lower()
        if  file_ext == ".json":
            content_type = "application/json"
        elif file_ext == ".txt":
            content_type = "text/plain"
        elif file_ext == ".srt" or format.lower() == "srt":
            content_type = "text/srt"
        else:  # Default to HTML
            content_type = "text/html"
        
        base_name = os.path.splitext(file_name)[0]
        if content_type == "text/plain" or content_type == "application/json":
            # Generate text content from HTML
            from main import prepare_download
            prepare_download(base_name, job_id)
            html_path = join(out_path, base_name + ".htmlfinal")
            
            if not os.path.exists(html_path):
                raise HTTPException(status_code=404, detail="HTML file not found")
            
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Extract text content using similar logic to downloadText in viewer.py
            text_content = ""
            
            # Parse HTML content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all segments with speakers
            editor_div = soup.find(id="editor")
            if not editor_div:
                raise HTTPException(status_code=500, detail="Could not parse HTML content")
            
            # Group text by speaker
            speaker_texts = {}


            last_speaker = None
            last_timestamp = None
            for div in editor_div.find_all('div', recursive=False):
                # Look for speaker selection
                selected = div.find(attrs={"selected": "selected"})
                if not selected:
                    continue

                speaker_name = selected.text
                timestamp_span = div.find('span', contenteditable="true")
                if not timestamp_span:
                    continue

                timestamp = timestamp_span.text

                # Check if this is a foreign language segment
                language_checkbox = div.find('input', {'class': 'language'})
                is_foreign = language_checkbox and language_checkbox.has_attr('checked')

                # Skip foreign language segments if ignore_lang is checked
                # For API we always include all languages
                if is_foreign:
                    # We still process it but mark it
                    pass

                # Find the paragraph with text segments
                p_tag = div.find_next('p')
                if not p_tag:
                    continue

                segments = p_tag.find_all('span', class_="segment")
                if not segments:
                    continue

                # Combine all segments for this speaker
                segment_text = " ".join([seg.text.strip() for seg in segments])

                if speaker_name != last_speaker:
                    last_speaker = speaker_name
                    last_timestamp = timestamp

                speaker_key = f"{last_speaker} ({last_timestamp})"


                # Add to our collection, combining with existing text if same speaker
                if speaker_key in speaker_texts:
                    speaker_texts[speaker_key] += " " + segment_text
                else:
                    speaker_texts[speaker_key] = segment_text

            # Second pass: build the output text
            for speaker_key, text in speaker_texts.items():
                if text_content:
                    text_content += "\n\n"
                text_content += f"{speaker_key}:\n{text.strip()}"
            content = text_content

        elif content_type == "text/html":
            # Prepare HTML file for download
            from main import prepare_download
            prepare_download(base_name, job_id)
            file_path = join(out_path, base_name + ".htmlfinal")
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:  # SRT
            file_path = join(out_path, base_name + ".srt")
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        if (content_type == 'text/plain' or content_type == 'text/srt'):
            # return as text/plain without JSONResponse
            return PlainTextResponse(content)

        if (content_type == 'text/html'):
            # return as text/html without JSONResponse
            return HTMLResponse(content)
        return JSONResponse(
            content={"content": content},
            media_type="application/json"
        )
    
    return router
