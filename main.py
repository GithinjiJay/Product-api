import logging
import os
import platform
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import psutil
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth import (
    create_access_token,
    get_current_admin,
    get_current_user,
    hash_password,
    verify_password,
)
from database.session import create_tables, get_session
from models.product import Product, ProductCreate, ProductRead, ProductUpdate
from models.user import User, UserCreate, UserResponse

start_time = time.time()

# Configure logging
LOG_FILE = os.getenv("LOG_FILE", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Product API", version="1.0.0")


# This is the app startup event.
@app.on_event("startup")
def on_startup():
    create_tables()


# This is the HTTP error handler.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail},
        headers=getattr(exc, "headers", None),
    )
from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# This is the validation error handler.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
        },
    )


# This is the request logging middleware.
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response


# This is the health check endpoint.
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime": time.time() - start_time,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }


# This is the metrics endpoint.
@app.get("/metrics")
def get_metrics(current_user: User = Depends(get_current_admin)):
    """Metrics endpoint for monitoring (admin only)."""
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage("/").percent,
    }


# This is the register endpoint.
@app.post("/register", response_model=UserResponse, status_code=201)
def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session),
):
    """Register a new user."""
    existing = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing:
        raise HTTPException(409, "Username already exists")

    existing = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing:
        raise HTTPException(409, "Email already exists")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


# This is the login endpoint.
@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Login and receive an access token."""
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "User is inactive")

    user.last_login = datetime.utcnow()
    session.commit()

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
        "username": user.username,
        "role": user.role,
    }


# This is the list users endpoint.
@app.get("/users", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """List all users (admin only)."""
    return session.exec(select(User)).all()


# This is the create product endpoint.
@app.post("/products", response_model=ProductRead, status_code=201)
def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create a product."""
    product = Product(**product_data.dict())
    session.add(product)
    session.commit()
    session.refresh(product)

    return product


# This is the list products endpoint.
@app.get("/products", response_model=list[ProductRead])
def list_products(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List products."""
    return session.exec(select(Product)).all()


# This is the get single product endpoint.
@app.get("/products/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get a single product."""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    return product


# This is the update product endpoint.
@app.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update a product."""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    for key, value in product_update.dict(exclude_unset=True).items():
        setattr(product, key, value)

    product.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(product)

    return product


# This is the delete product endpoint.
@app.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a product."""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    session.delete(product)
    session.commit()

    return Response(status_code=204)