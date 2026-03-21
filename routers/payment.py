from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import supabase
from services.razorpay_service import verify_signature
from services.email_service import send_booking_confirmation, notify_admin

router = APIRouter()


class VerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_id: str


@router.post("/verify")
def verify_payment(req: VerifyRequest):
    # 1. Verify Razorpay signature
    if not verify_signature(
        req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature
    ):
        raise HTTPException(400, "Payment verification failed")

    # 2. Update payment record
    supabase.table("payments").update(
        {
            "razorpay_payment_id": req.razorpay_payment_id,
            "razorpay_signature": req.razorpay_signature,
            "status": "paid",
        }
    ).eq("razorpay_order_id", req.razorpay_order_id).execute()

    # 3. Update booking status
    supabase.table("demo_bookings").update(
        {
            "payment_status": "paid",
            "razorpay_payment_id": req.razorpay_payment_id,
            "razorpay_order_id": req.razorpay_order_id,
            "status": "confirmed",
        }
    ).eq("id", req.booking_id).execute()

    # 4. Get full booking details for emails
    booking = (
        supabase.table("demo_bookings")
        .select("*")
        .eq("id", req.booking_id)
        .execute()
        .data[0]
    )

    # 5. Send confirmation email to parent
    try:
        send_booking_confirmation(booking)
    except Exception as e:
        print(f"Email to parent failed: {e}")

    # 6. Notify VR Robotics admin
    try:
        notify_admin(booking)
    except Exception as e:
        print(f"Admin email failed: {e}")

    return {"status": "success", "message": "Payment verified, emails sent"}
