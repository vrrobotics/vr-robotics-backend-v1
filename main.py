from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, booking, payment, contact, admin
from config import settings

app = FastAPI(title="VR Robotics Academy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
app.include_router(contact.router, prefix="/api/contact", tags=["Contact"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
def root():
    return {"status": "running", "service": "VR Robotics Academy API"}


@app.get("/health")
def health():
    return {"status": "ok"}
