import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vicentereyes.org",
        "https://www.vicentereyes.org"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCORD_WEBHOOK_URL = os.environ.get("FASTAPI_DISCORD_WEBHOOK_URL")  # Replace with your actual Discord webhook URL

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
async def submit_form(form_data: FormData):
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
        
        return {"message": "Form data sent to Discord successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
