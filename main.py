import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

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
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Environment variables
DISCORD_WEBHOOK_URL = os.environ.get("FASTAPI_DISCORD_WEBHOOK_URL")
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY")

# Define the request body model with Turnstile token
class FormData(BaseModel):
    name: str
    email: str
    message: str
    service: str
    companyName: str
    companyUrl: str

@app.post("/submit/")
@app.post("/submit")  # Handle both with and without trailing slash
async def submit_form(form_data: FormData):
    try:
        # Format the message for Discord
        message_content = {
            "content": f"New form submission: \n"
                      f"**Name:** {form_data.name}\n"
                      f"**Email:** {form_data.email}\n"
                      f"**Message:** {form_data.message}\n"
                      f"**Service:** {form_data.service}\n"
                      f"**Company Name:** {form_data.companyName}\n"
                      f"**Company URL:** {form_data.companyUrl}"
        }

        # Send to Discord webhook
        async with httpx.AsyncClient() as client:
            response = await client.post(DISCORD_WEBHOOK_URL, json=message_content)

        if response.status_code != 204:
            raise HTTPException(status_code=response.status_code, 
                              detail="Failed to send message to Discord")

        return {"message": "Form data sent to Discord successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))