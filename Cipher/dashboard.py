from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import os
import requests

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-super-secret-session-key")

app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/callback")
OAUTH_SCOPE = "identify guilds"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login")
def login():
    return RedirectResponse(
        f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope={OAUTH_SCOPE}"
    )

@app.get("/callback")
def callback(request: Request, code: str):
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": OAUTH_SCOPE,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    access_token = response.json().get("access_token")

    user_resp = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    request.session["user"] = user_resp.json()
    return RedirectResponse("/")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

@app.get("/serverinfo", response_class=HTMLResponse)
async def serverinfo(request: Request):
    return templates.TemplateResponse("serverinfo.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("dashboard:app", host="127.0.0.1", port=8000, reload=True)
