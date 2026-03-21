from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from database import supabase

router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str = None
    message: str


@router.post("/submit")
def submit_contact(req: ContactRequest):
    # Save contact message to Supabase
    supabase.table("contact_messages").insert(
        {
            "name": req.name,
            "email": req.email,
            "phone": req.phone,
            "message": req.message,
        }
    ).execute()

    return {"message": "Message received. We'll respond within 24 hours."}
