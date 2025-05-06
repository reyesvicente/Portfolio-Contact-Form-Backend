import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import secrets
from datetime import datetime
from fastapi.responses import JSONResponse

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vicentereyes.org",
        "https://www.vicentereyes.org",
        "https://dev.vicentereyes.org",
        "https://staging.vicentereyes.org"
    ],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

# Environment variables
DISCORD_WEBHOOK_URL = os.environ.get("FASTAPI_DISCORD_WEBHOOK_URL")

# CSRF token storage
csrf_tokens = {}

def generate_csrf_token():
    return secrets.token_hex(32)

@app.get("/api/csrf-token")
async def get_csrf_token(request: Request):
    # Generate a new CSRF token
    csrf_token = generate_csrf_token()
    
    # Store the token with an expiration time (1 hour)
    csrf_tokens[csrf_token] = {
        "timestamp": datetime.now(),
        "ip": request.client.host
    }
    
    # Set the CSRF token in a cookie
    response = JSONResponse({"csrfToken": csrf_token})
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response

# Define the request body model
class FormData(BaseModel):
    name: str
    email: str
    message: str
    service: str
    companyName: str
    companyUrl: str

@app.post("/submit/")
@app.post("/submit")
async def submit_form(form_data: FormData, request: Request):
    # Verify CSRF token
    csrf_token = request.cookies.get("csrf_token")
    if not csrf_token or csrf_token not in csrf_tokens:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Prepare the message content for Discord
        message_content = {
            "content": f"New form submission: \n"
                            f"**Name:** {form_data.name}\n"
                            f"**Email:** {form_data.email}\n"
                            f"**Message:** {form_data.message}\n"
                            f"**Service:** {form_data.service}\n"
                            f"**Company Name:** {form_data.companyName}\n"
                            f"**Company URL:** {form_data.companyUrl}"
        }

        # Send the message to the Discord webhook URL
        async with httpx.AsyncClient() as client:
            response = await client.post(DISCORD_WEBHOOK_URL, json=message_content)

        # Check if the request was successful
        if response.status_code != 204:
            raise HTTPException(status_code=response.status_code, detail="Failed to send message to Discord")
        
        return {"message": "Form data sent to Discord successfully", "success": True}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
