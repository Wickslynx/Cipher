from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import requests
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="dashboard/templates")

# Mock data for tickets demonstration - replace with actual DB in production
sample_tickets = [
    {
        "id": "1001",
        "title": "Bot not responding to commands",
        "content": "The bot doesn't respond when I use the !help command in my server.",
        "status": "open",
        "created_at": "Apr 12, 2025",
        "user": {
            "name": "User1#1234",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
        }
    },
    {
        "id": "1002",
        "title": "Feature request: Role assignment",
        "content": "Can you add a feature to automatically assign roles when users join?",
        "status": "pending",
        "created_at": "Apr 10, 2025",
        "user": {
            "name": "User2#5678",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/1.png"
        }
    },
    {
        "id": "1003",
        "title": "Ticket system explanation",
        "content": "How do I set up the ticket system in my server?",
        "status": "closed",
        "created_at": "Apr 5, 2025",
        "user": {
            "name": "User3#9012",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/2.png"
        }
    }
]

@router.get("/tickets", response_class=HTMLResponse)
async def tickets_page(request: Request, guild_id: Optional[str] = None):
    # Check if user is logged in
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/")
    
    # In a real implementation, we would filter tickets by guild_id
    # For now, we'll just use our sample data
    
    return templates.TemplateResponse("tickets.html", {
        "request": request,
        "user": user,
        "tickets": sample_tickets,
        "guild_id": guild_id
    })

@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(request: Request, ticket_id: str):
    # Check if user is logged in
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/")
    
    # Find the ticket (in a real app, this would be a database query)
    ticket = next((t for t in sample_tickets if t["id"] == ticket_id), None)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return templates.TemplateResponse("ticket_detail.html", {
        "request": request,
        "user": user,
        "ticket": ticket
    })

@router.post("/tickets/create")
async def create_ticket(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...)
):
    # Check if user is logged in
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/")
    
    # In a real implementation, we would save the ticket to a database
    # For now, we'll just redirect back to the tickets page
    
    return RedirectResponse("/tickets", status_code=303)  # POST/Redirect/GET pattern
