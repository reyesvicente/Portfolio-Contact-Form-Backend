import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import logging

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vicentereyes.org",
        "https://www.vicentereyes.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1298557347165241364/QAeVWEQHuhbHPGK6FCg3KrE0Aj7vYSH0pyIhZ6JGntkS2GhtOUvesMPoap6IRxLAXDoo"
CLOUDFLARE_TURNSTILE_SECRET = "0x4AAAAAABDoaBPfTgbaZKIrVCf54uNqykU"

# Ensure required environment variables are set
if not DISCORD_WEBHOOK_URL:
    raise ValueError("Environment variable FASTAPI_DISCORD_WEBHOOK_URL is not set")
if not CLOUDFLARE_TURNSTILE_SECRET:
    raise ValueError("Environment variable CLOUDFLARE_TURNSTILE_SECRET is not set")

# Define the request body model
class FormData(BaseModel):
    name: str
    email: str
    message: str
    service: str
    companyName: str
    companyUrl: Optional[str] = None  # Make companyUrl optional
    turnstile_token: str = Field(..., alias="cf-turnstile-response")

async def verify_turnstile_token(token: str) -> bool:
    """
    Verify the Turnstile token using Cloudflare's API.
    """
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": CLOUDFLARE_TURNSTILE_SECRET,
        "response": token
    }
    logger.info(f"Verifying Turnstile token: {token}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)
            logger.info(f"Turnstile API response status: {response.status_code}")
            logger.info(f"Turnstile API response body: {response.text}")
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Turnstile verification result: {result}")
                if not result.get("success", False):
                    logger.error(f"Turnstile verification failed with error-codes: {result.get('error-codes')}")
                return result.get("success", False)
            else:
                logger.error(f"Turnstile verification failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error verifying Turnstile token: {e}")
    return False

@app.post("/submit/")
@app.post("/submit")
async def submit_form(form_data: FormData):
    """
    Handle form submission and send data to Discord.
    """
    logger.info(f"Received form data: {form_data.dict()}")
    # Verify the Turnstile token
    is_valid_token = await verify_turnstile_token(form_data.turnstile_token)
    if not is_valid_token:
        logger.error("Invalid Turnstile token received")
        raise HTTPException(status_code=400, detail="Invalid Turnstile token")

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
            logger.error(f"Failed to send message to Discord: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to send message to Discord")
        
        logger.info("Form data sent to Discord successfully")
        return {"message": "Form data sent to Discord successfully"}
    
    except Exception as e:
        logger.error(f"Error processing form submission: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
