import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import secrets
<<<<<<< HEAD
from datetime import datetime, timedelta # Import timedelta
=======
from datetime import datetime, timedelta 
>>>>>>> e228f51 (added hcaptcha verification)
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
<<<<<<< HEAD
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY") # You need to set this environment variable
=======
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY") 
>>>>>>> e228f51 (added hcaptcha verification)

# CSRF token storage
csrf_tokens = {}

def generate_csrf_token():
    return secrets.token_hex(32)

@app.get("/api/csrf-token")
async def get_csrf_token(request: Request):
    # Generate a new CSRF token
    csrf_token = generate_csrf_token()
    
    # Store the token with an expiration time (1 hour)
    expiration_time = datetime.now() + timedelta(hours=1) # Set expiration time
    csrf_tokens[csrf_token] = {
        "timestamp": datetime.now(),
        "expires": expiration_time, # Store expiration time
        "ip": request.client.host
    }
    
    # Set the CSRF token in a cookie
    response = JSONResponse({"csrfToken": csrf_token})
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=int(expiration_time.timestamp()) # Set cookie expiration
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
    h_captcha_response: str # Added hCaptcha response field

@app.post("/submit/")
async def submit_form(form_data: FormData, request: Request):
    # Verify CSRF token
    csrf_token = request.cookies.get("csrf_token")
    if not csrf_token or csrf_token not in csrf_tokens:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    # Check if CSRF token has expired
    if datetime.now() > csrf_tokens[csrf_token]["expires"]:
        del csrf_tokens[csrf_token] # Remove expired token
        raise HTTPException(status_code=400, detail="CSRF token expired. Please refresh the page.")

    # Verify hCaptcha token
    if not HCAPTCHA_SECRET_KEY:
        raise HTTPException(status_code=500, detail="hCaptcha secret key not configured on the server.")

    hcaptcha_verification_data = {
        'secret': HCAPTCHA_SECRET_KEY,
        'response': form_data.h_captcha_response,
        'remoteip': request.client.host
    }

    try:
        async with httpx.AsyncClient() as client:
            hcaptcha_response = await client.post(
                "https://hcaptcha.com/siteverify",
                data=hcaptcha_verification_data
            )
            hcaptcha_response.raise_for_status() # Raise an exception for bad status codes
            hcaptcha_result = hcaptcha_response.json()

            if not hcaptcha_result.get("success"):
                print(f"hCaptcha verification failed: {hcaptcha_result.get('error-codes')}")
                raise HTTPException(status_code=400, detail="hCaptcha verification failed. Please try again.")

        # Delete the used CSRF token to prevent replay attacks
        del csrf_tokens[csrf_token]
        
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
    
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while communicating with external services: {exc}")
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error during hCaptcha verification: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=500, detail="Failed to verify hCaptcha. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))