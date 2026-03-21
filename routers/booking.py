from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from database import supabase
from config import settings
from services.razorpay_service import create_order

router = APIRouter()


class BookDemoRequest(BaseModel):
    parent_name: str
    email: EmailStr
    phone: str
    child_name: str
    child_age: int = None
    preferred_date: str = None
    preferred_time: str = None
    interests: str = None
    message: str = None


@router.post("/book-demo")
def book_demo(req: BookDemoRequest):
    # 1. Save booking to Supabase
    booking = (
        supabase.table("demo_bookings")
        .insert(
            {
                "parent_name": req.parent_name,
                "email": req.email,
                "phone": req.phone,
                "child_name": req.child_name,
                "child_age": req.child_age,
                "preferred_date": req.preferred_date,
                "preferred_time": req.preferred_time,
                "interests": req.interests,
                "message": req.message,
                "amount": 49,
            }
        )
        .execute()
    )
    bid = booking.data[0]["id"]

    # 2. Create Razorpay order (amount in paise: 49 INR = 4900 paise)
    order = create_order(
        amount_paise=4900,
        receipt=f"demo_{bid[:8]}",
        notes={"booking_id": bid, "child": req.child_name},
    )

    # 3. Save payment record
    supabase.table("payments").insert(
        {
            "booking_id": bid,
            "razorpay_order_id": order["id"],
            "amount": 49,
            "status": "created",
        }
    ).execute()

    # 4. Return order details to frontend for Razorpay checkout
    return {
        "booking_id": bid,
        "order_id": order["id"],
        "key": settings.RAZORPAY_KEY_ID,
        "amount": 4900,
        "currency": "INR",
    }
