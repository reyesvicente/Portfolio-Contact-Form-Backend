import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

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
        "https://dev.vicentereyes.org",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Environment variables
DISCORD_WEBHOOK_URL = os.getenv("FASTAPI_DISCORD_WEBHOOK_URL")

# Ensure required environment variables are set
if not DISCORD_WEBHOOK_URL:
    raise ValueError("Environment variable FASTAPI_DISCORD_WEBHOOK_URL is not set")

# Define the request body model
class FormData(BaseModel):
    name: str
    email: str
    message: str
    service: str
    companyName: str
    companyUrl: Optional[str] = None

@app.post("/submit/")
@app.post("/submit")
async def submit_form(form_data: FormData):
    """
    Handle form submission and send data to Discord.
    """
    logger.info(f"Received form data: {form_data.dict()}")
    
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