import os
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import secrets
from datetime import datetime, timedelta
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
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY")

# CSRF token storage
# Using a dictionary for in-memory storage. For production, consider a more persistent and scalable solution
# like a dedicated cache (Redis) or database.
csrf_tokens = {}

def generate_csrf_token():
    return secrets.token_hex(32)

@app.get("/api/csrf-token")
async def get_csrf_token(request: Request, response: Response): # Add Response parameter
    # Generate a new CSRF token
    csrf_token = generate_csrf_token()

    # Store the token with an expiration time (1 hour)
    expiration_time = datetime.now() + timedelta(hours=1)
    csrf_tokens[csrf_token] = {
        "timestamp": datetime.now(),
        "expires": expiration_time,
        "ip": request.client.host # Storing IP can be useful for debugging/auditing
    }

    # Set the CSRF token in an HttpOnly, Secure, SameSite=Lax cookie
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        secure=True, # Ensure this is True in production (HTTPS)
        samesite="lax", # Recommended for CSRF protection
        expires=int(expiration_time.timestamp()) # Set cookie expiration as a timestamp
    )
    return {"csrfToken": csrf_token} # Return the token in the JSON response as well for client-side use if needed

# Define the request body model
class FormData(BaseModel):
    name: str
    email: str
    message: str
    service: str
    companyName: str
    companyUrl: str
    h_captcha_response: str # hCaptcha response field

@app.post("/submit/")
async def submit_form(form_data: FormData, request: Request):
    # Verify CSRF token
    csrf_token = request.headers.get("X-CSRF-Token") # Get CSRF token from header, not cookie for POST
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
        'remoteip': request.client.host # IP address of the client
    }

    try:
        async with httpx.AsyncClient() as client:
            hcaptcha_response = await client.post(
                "https://hcaptcha.com/siteverify",
                data=hcaptcha_verification_data
            )
            hcaptcha_response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
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

        # Check if the request to Discord was successful
        if response.status_code != 204: # Discord returns 204 No Content on success
            print(f"Failed to send message to Discord: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Failed to send message to Discord.")

        return {"message": "Form data sent to Discord successfully", "success": True}

    except httpx.RequestError as exc:
        # Catch network-related errors during external service calls
        raise HTTPException(status_code=500, detail=f"A network error occurred while communicating with external services: {exc}")
    except httpx.HTTPStatusError as exc:
        # Catch HTTP status errors (4xx or 5xx) from external services
        print(f"HTTP error during hCaptcha verification or Discord webhook: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=500, detail="An external service returned an error. Please try again later.")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")