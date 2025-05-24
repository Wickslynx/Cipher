from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import discord
import requests

router = APIRouter()
templates = Jinja2Templates(directory="dashboard/templates")

@router.get("/serverinfo", response_class=HTMLResponse)
async def server_info(request: Request):
    # Check if user is logged in
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/")
    
    bot = request.app.state.bot
    guild_id = request.query_params.get("guild_id")
    
    # If guild_id is provided, validate and convert to int
    if guild_id:
        try:
            guild_id = int(guild_id)
        except ValueError:
            return RedirectResponse("/")
    
    # Get user's guilds to verify access
    if "access_token" not in request.session:
        return RedirectResponse("/login")
    
    headers = {"Authorization": f"Bearer {request.session['access_token']}"}
    guilds_resp = requests.get("https://discord.com/api/users/@me/guilds", headers=headers)
    
    if guilds_resp.status_code != 200:
        return RedirectResponse("/login")
    
    user_guilds = guilds_resp.json()
    user_guild_ids = [int(g["id"]) for g in user_guilds]
    
    # Get bot guilds
    bot_guilds = bot.guilds
    bot_guild_ids = [g.id for g in bot_guilds]
    
    # Find common guilds (where bot and user are both present)
    common_guild_ids = set(user_guild_ids).intersection(set(bot_guild_ids))
    
    if not common_guild_ids:
        return templates.TemplateResponse("serverinfo.html", {
            "request": request,
            "user": user,
            "server": None,
            "error": "You don't have any servers with this bot"
        })
    
    # Find selected guild or default to first common guild
    guild = None
    if guild_id and guild_id in common_guild_ids:
        guild = discord.utils.get(bot_guilds, id=guild_id)
    elif common_guild_ids:
        first_common_id = list(common_guild_ids)[0]
        guild = discord.utils.get(bot_guilds, id=first_common_id)
    
    if not guild:
        return RedirectResponse("/")
    
    # Generate invite link for the bot
    invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(administrator=True))
    
    # Prepare server data
    server_data = {
        "name": guild.name,
        "id": guild.id,
        "member_count": guild.member_count,
        "roles": [{"name": role.name, "color": str(role.color)} for role in guild.roles if not role.is_default()],
        "text_channels": [{"name": channel.name, "id": channel.id} 
                           for channel in guild.channels if isinstance(channel, discord.TextChannel)],
        "voice_channels": [{"name": channel.name, "id": channel.id} 
                            for channel in guild.channels if isinstance(channel, discord.VoiceChannel)],
        "invite_url": invite,
        "icon_url": guild.icon.url if guild.icon else None
    }
    
    # Get common guilds to display in sidebar
    common_guilds = [g for g in user_guilds if int(g["id"]) in common_guild_ids]
    
    return templates.TemplateResponse("serverinfo.html", {
        "request": request,
        "user": user,
        "server": server_data,
        "guilds": common_guilds
    })
