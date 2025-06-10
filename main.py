import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1298557347165241364/QAeVWEQHuhbHPGK6FCg3KrE0Aj7vYSH0pyIhZ6JGntkS2GhtOUvesMPoap6IRxLAXDoo"

app = FastAPI()

origins = [
    "https://vicentereyes.org",
    "https://www.vicentereyes.org"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
