import requests

url = "https://portfolio-contact-form-backend.vercel.app/submit/"
data = {
    "companyName": "aaaaaaa",
    "companyUrl": "https://www.adminero.com",  # Ensure this is a valid URL
    "name": "Admin",
    "email": "acy77696@nowni.com",
    "message": "awaaaaaaaaaaaa",
    "service": "Landing Page Development",
}

response = requests.post(url, json=data)
print(response.json())
