from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from database import supabase
from config import settings

router = APIRouter()
security = HTTPBearer()
pwd_ctx = CryptContext(schemes=["bcrypt"])


# ── Auth guard ────────────────────────────────────────────────────────────────
def get_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            creds.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("role") != "admin":
            raise HTTPException(403, "Admin access only")
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


# ── Request models ────────────────────────────────────────────────────────────
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # "student" | "teacher"
    phone: str = None
    age: int = None
    gender: str = None
    specialisation: str = None  # for teachers


class ResetPasswordRequest(BaseModel):
    new_password: str


class UpdateCredentialsRequest(BaseModel):
    email: EmailStr = None
    new_password: str = None
    full_name: str = None
    phone: str = None
    specialisation: str = None


# ── List endpoints ────────────────────────────────────────────────────────────
@router.get("/students")
def list_students(admin=Depends(get_admin)):
    return (
        supabase.table("users")
        .select("id,email,full_name,role,status,phone,age,gender,created_at")
        .eq("role", "student")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/teachers")
def list_teachers(admin=Depends(get_admin)):
    return (
        supabase.table("users")
        .select("id,email,full_name,role,status,phone,specialisation,created_at")
        .eq("role", "teacher")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/bookings")
def list_bookings(admin=Depends(get_admin)):
    return (
        supabase.table("demo_bookings")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/contacts")
def list_contacts(admin=Depends(get_admin)):
    return (
        supabase.table("contact_messages")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/stats")
def get_stats(admin=Depends(get_admin)):
    students = supabase.table("users").select("id", count="exact").eq("role", "student").execute()
    teachers = supabase.table("users").select("id", count="exact").eq("role", "teacher").execute()
    bookings = supabase.table("demo_bookings").select("id", count="exact").execute()
    paid = (
        supabase.table("demo_bookings")
        .select("id", count="exact")
        .eq("payment_status", "paid")
        .execute()
    )
    pending_students = (
        supabase.table("users")
        .select("id", count="exact")
        .eq("role", "student")
        .eq("status", "pending")
        .execute()
    )
    pending_teachers = (
        supabase.table("users")
        .select("id", count="exact")
        .eq("role", "teacher")
        .eq("status", "pending")
        .execute()
    )

    return {
        "total_students": students.count or 0,
        "total_teachers": teachers.count or 0,
        "total_bookings": bookings.count or 0,
        "paid_bookings": paid.count or 0,
        "pending_students": pending_students.count or 0,
        "pending_teachers": pending_teachers.count or 0,
    }


# ── Approve / Reject ──────────────────────────────────────────────────────────
@router.post("/approve/{user_id}")
def approve_user(user_id: str, admin=Depends(get_admin)):
    supabase.table("users").update({"status": "approved"}).eq("id", user_id).execute()
    return {"message": "User approved"}


@router.post("/reject/{user_id}")
def reject_user(user_id: str, admin=Depends(get_admin)):
    supabase.table("users").update({"status": "rejected"}).eq("id", user_id).execute()
    return {"message": "User rejected"}


@router.delete("/delete/{user_id}")
def delete_user(user_id: str, admin=Depends(get_admin)):
    supabase.table("users").delete().eq("id", user_id).execute()
    return {"message": "User deleted"}


# ── Admin creates user directly (status: approved immediately) ────────────────
@router.post("/create-user")
def create_user(req: CreateUserRequest, admin=Depends(get_admin)):
    existing = supabase.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(400, "Email already registered")

    payload = {
        "email": req.email,
        "password_hash": pwd_ctx.hash(req.password),
        "full_name": req.full_name,
        "role": req.role,
        "phone": req.phone,
        "age": req.age,
        "gender": req.gender,
        "status": "approved",  # Admin-created users are immediately approved
    }
    if req.specialisation:
        payload["specialisation"] = req.specialisation

    user = supabase.table("users").insert(payload).execute()
    return {
        "message": f"{req.role.title()} created and approved.",
        "user_id": user.data[0]["id"],
        "email": req.email,
        "role": req.role,
    }


# ── Admin resets any user's password ─────────────────────────────────────────
@router.put("/reset-password/{user_id}")
def reset_password(user_id: str, req: ResetPasswordRequest, admin=Depends(get_admin)):
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    supabase.table("users").update(
        {"password_hash": pwd_ctx.hash(req.new_password)}
    ).eq("id", user_id).execute()

    return {"message": "Password reset successfully"}


# ── Admin updates user credentials / details ──────────────────────────────────
@router.put("/update-user/{user_id}")
def update_user(user_id: str, req: UpdateCredentialsRequest, admin=Depends(get_admin)):
    updates = {}

    if req.email:
        # Check email not taken by another user
        existing = (
            supabase.table("users")
            .select("id")
            .eq("email", req.email)
            .neq("id", user_id)
            .execute()
        )
        if existing.data:
            raise HTTPException(400, "Email already in use by another account")
        updates["email"] = req.email

    if req.new_password:
        if len(req.new_password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        updates["password_hash"] = pwd_ctx.hash(req.new_password)

    if req.full_name:
        updates["full_name"] = req.full_name

    if req.phone:
        updates["phone"] = req.phone

    if req.specialisation is not None:
        updates["specialisation"] = req.specialisation

    if not updates:
        raise HTTPException(400, "No fields to update")

    supabase.table("users").update(updates).eq("id", user_id).execute()
    return {"message": "User updated successfully"}