from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import os
import requests
from dashboard.routes import serverinfo  # import the router
from main import bot

app = FastAPI()
app.include_router(serverinfo.router)  # Include the serverinfo router
app.add_middleware(SessionMiddleware, secret_key="kr-SFxxufJpd3snBh-gqOm2Kzw7r4ZyP")
app.state.bot = bot  

app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1361017411746136145")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "CLIENTSECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/callback")
OAUTH_SCOPE = "identify guilds"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    
    # Fetch guilds if user is logged in
    guilds = []
    if user and "access_token" in request.session:
        headers = {"Authorization": f"Bearer {request.session['access_token']}"}
        guilds_resp = requests.get("https://discord.com/api/users/@me/guilds", headers=headers)
        if guilds_resp.status_code == 200:
            guilds = guilds_resp.json()
    
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "guilds": guilds})

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
    
    if response.status_code == 200:
        token_data = response.json()
        # Store the access token in the session
        request.session["access_token"] = token_data.get("access_token")
        
        # Get user data
        user_resp = requests.get("https://discord.com/api/users/@me", 
                               headers={"Authorization": f"Bearer {token_data.get('access_token')}"})
        
        if user_resp.status_code == 200:
            request.session["user"] = user_resp.json()
    
    return RedirectResponse("/")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# Remove the duplicate serverinfo route from here

if __name__ == "__main__":
    uvicorn.run("website:app", host="127.0.0.1", port=8000, reload=True)
