import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt

from database import supabase
from config import settings
from services.email_service import send_email

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"])


# ── Hardcoded admin accounts ─────────────────────────────────────────────────
ADMIN_ACCOUNTS = {
    "abhinavneeraj.bade@gmail.com": "27Sep@2006",
    "md@vrroboticsacademy.com":     "hello",
}


# ── Models ────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "student"
    phone: str = None
    age: int = None
    gender: str = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_token(user_id: str, role: str, name: str = "", email: str = "") -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "name": name,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


# ── 1. Signup ─────────────────────────────────────────────────────────────────
@router.post("/signup")
def signup(req: SignupRequest):
    if req.role == "admin":
        raise HTTPException(400, "Admin accounts cannot be self-registered")

    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    existing = supabase.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(400, "Email already registered")

    user = (
        supabase.table("users")
        .insert({
            "email": req.email,
            "password_hash": pwd_ctx.hash(req.password),
            "full_name": req.full_name,
            "role": req.role,
            "phone": req.phone,
            "age": req.age,
            "gender": req.gender,
            "status": "pending",
        })
        .execute()
    )

    # Notify admin about new registration
    try:
        html = f"""
        <div style="font-family:Arial;max-width:500px;margin:0 auto;padding:20px">
          <h2 style="color:#FF6A00">🆕 New {req.role.title()} Registration</h2>
          <p><b>Name:</b> {req.full_name}</p>
          <p><b>Email:</b> {req.email}</p>
          <p><b>Role:</b> {req.role}</p>
          <p><b>Phone:</b> {req.phone or '—'}</p>
          <p style="color:#888">Login to admin dashboard to approve or reject.</p>
        </div>
        """
        send_email(settings.VR_ADMIN_EMAIL, f"🆕 New {req.role}: {req.full_name}", html)
    except Exception as e:
        print(f"Admin notification failed: {e}")

    return {
        "message": f"{req.role.title()} registration submitted. Pending admin approval.",
        "user_id": user.data[0]["id"],
    }


# ── 2. Login ──────────────────────────────────────────────────────────────────
@router.post("/login")
def login(req: LoginRequest):
    # 1. Hardcoded admin accounts
    if req.email in ADMIN_ACCOUNTS:
        if ADMIN_ACCOUNTS[req.email] != req.password:
            raise HTTPException(401, "Invalid credentials")
        return {
            "token": _make_token("admin-hardcoded", "admin", "Admin", req.email),
            "role": "admin",
            "name": "Admin",
            "email": req.email,
            "status": "approved",
        }

    # 2. Database users
    result = supabase.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        raise HTTPException(401, "Invalid email or password")

    user = result.data[0]

    if not user.get("password_hash") or not pwd_ctx.verify(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    if user["status"] == "pending":
        raise HTTPException(403, "Account pending admin approval. Please wait.")
    if user["status"] == "rejected":
        raise HTTPException(403, "Account rejected. Contact admin via WhatsApp +91 7483430092.")

    return {
        "token": _make_token(user["id"], user["role"], user["full_name"], user["email"]),
        "role": user["role"],
        "name": user["full_name"],
        "email": user["email"],
        "status": user["status"],
    }


# ── 3. Forgot Password — sends OTP via Brevo email ───────────────────────────
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    result = (
        supabase.table("users")
        .select("id,full_name")
        .eq("email", req.email)
        .execute()
    )

    if result.data:
        user = result.data[0]
        otp = _generate_otp()
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

        # Store OTP in DB
        supabase.table("users").update({
            "reset_otp": otp,
            "reset_otp_expires": expires,
        }).eq("id", user["id"]).execute()

        # Send OTP via Brevo SMTP
        try:
            html = f"""
            <div style="font-family:Arial;max-width:500px;margin:0 auto;padding:20px">
              <h2 style="color:#FF6A00">🔑 Password Reset</h2>
              <p>Dear {user['full_name']},</p>
              <p>You requested a password reset for your VR Robotics Academy account.</p>
              <p>Your OTP code is:</p>
              <div style="background:#1a1a1a;border:2px solid #FF6A00;border-radius:12px;
                          padding:24px;text-align:center;margin:20px 0">
                <span style="font-size:36px;font-weight:900;letter-spacing:8px;color:#FF6A00">
                  {otp}
                </span>
              </div>
              <p style="color:#888">This code expires in <b>15 minutes</b>.</p>
              <p style="color:#888">If you didn't request this, ignore this email.</p>
              <hr style="border:none;border-top:1px solid #eee;margin:20px 0"/>
              <p style="color:#aaa;font-size:12px">— VR Robotics Academy, Hyderabad</p>
            </div>
            """
            send_email(req.email, "🔑 Password Reset OTP — VR Robotics", html)
        except Exception as e:
            print(f"OTP email failed for {req.email}: {e}")

    # Always same response (prevents email enumeration)
    return {
        "message": "If this email is registered, a 6-digit OTP has been sent. Check your inbox (and spam folder).",
        "otp_sent": True,
    }


# ── 4. Reset Password — verify OTP + set new password ────────────────────────
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    result = (
        supabase.table("users")
        .select("id,reset_otp,reset_otp_expires")
        .eq("email", req.email)
        .execute()
    )

    if not result.data:
        raise HTTPException(400, "Invalid email or OTP")

    user = result.data[0]

    # Verify OTP
    if not user.get("reset_otp") or user["reset_otp"] != req.otp:
        raise HTTPException(400, "Invalid OTP. Please check and try again.")

    # Check expiry
    if user.get("reset_otp_expires"):
        try:
            exp_str = user["reset_otp_expires"]
            if isinstance(exp_str, str):
                exp_str = exp_str.replace("Z", "+00:00")
            expires = datetime.fromisoformat(exp_str)
            now = datetime.utcnow()
            if expires.tzinfo:
                now = now.replace(tzinfo=expires.tzinfo)
            if now > expires:
                raise HTTPException(400, "OTP expired. Please request a new one.")
        except (ValueError, TypeError):
            pass

    # Update password + clear OTP
    supabase.table("users").update({
        "password_hash": pwd_ctx.hash(req.new_password),
        "reset_otp": None,
        "reset_otp_expires": None,
    }).eq("id", user["id"]).execute()

    return {"message": "Password reset successfully! You can now login with your new password."}


# ── 5. Me — current user from token ──────────────────────────────────────────
@router.get("/me")
def get_me(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "name": payload.get("name"),
            "email": payload.get("email"),
        }
    except Exception:
        raise HTTPException(401, "Invalid token")