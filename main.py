import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, status, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, select
from typing import List, Dict, Any, Optional

# 1. Imports from your local modules
from database.session import engine
from models.product import (
    Product, ProductCreate, ProductUpdate, ProductRead, StockAdjustment,
    Supplier, SupplierCreate, SupplierRead, SupplierUpdate
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Database Initialization Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

# 3. Initialize the FastAPI App instance FIRST
app = FastAPI(
    title="TechVault Inventory API",
    description="Robust API for managing electronics inventory with strict domain constraints.",
    version="1.0.0",
    lifespan=lifespan
)

# 4. Dependency to get database session
def get_db():
    with Session(engine) as session:
        yield session

# ==========================================
# 3. Global Exception Handlers (Standardized Exercise 5 Format)
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} at {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status_code": exc.status_code,
            "message": exc.detail,
            "errors": [],
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_name = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field_name,
            "message": error["msg"].replace("Value error, ", ""),
            "type": error["type"]
        })
        
    logger.warning(f"Validation failure at {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "status_code": 422,
            "message": "The data provided failed inventory validation rules.",
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database Integrity Error: {exc}")
    error_msg = str(exc.orig)
    message = "A database integrity conflict occurred."
    
    if "sku" in error_msg:
        message = "A product with this SKU already exists in the inventory."
    elif "name" in error_msg and "category" in error_msg:
        message = "A category with this name already exists."
    elif "supplier" in error_msg or "email" in error_msg:
        message = "A supplier with this name or email already exists."

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "status_code": 409,
            "message": message,
            "errors": [],
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled Server Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "status_code": 500,
            "message": "An unexpected internal server error occurred. Please try again later.",
            "errors": [],
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )

# ==========================================
# 6. API Endpoints / Routers (Must be below app definition)
# ==========================================

@app.get("/", tags=["General"])
def root():
    return {"message": "Welcome to the TechVault Inventory API", "docs": "/docs"}

# CREATE Product
@app.post("/products/", response_model=ProductRead, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_product(product_in: ProductCreate, session: Session = Depends(get_db)):
    db_product = Product.model_validate(product_in)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

# READ All Products
@app.get("/products/", response_model=List[ProductRead], tags=["Products"])
def read_products(offset: int = 0, limit: int = 100, session: Session = Depends(get_db)):
    products = session.exec(select(Product).offset(offset).limit(limit)).all()
    return products

# BULK UPDATE Products (Must be above dynamic '{product_id}' routes)
@app.patch("/products/bulk-update", tags=["Products"])
def bulk_update_price(
    category: str,
    discount_percent: float,
    session: Session = Depends(get_db)
) -> Dict[str, Any]:
    
    if not (0 < discount_percent < 100):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Discount percentage must be strictly between 0 and 100."
        )

    statement = select(Product).where(Product.category.ilike(category))
    products = session.exec(statement).all()

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No products found in category: '{category}'"
        )

    updated_count = 0
    for product in products:
        discount_amount = product.price * (discount_percent / 100)
        new_price = round(product.price - discount_amount, 2)

        if new_price < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bulk update aborted. Product '{product.name}' (SKU: {product.sku}) would drop to {new_price} KSh, which is below the 100 KSh minimum."
            )
        
        product.price = new_price
        updated_count += 1

    try:
        session.commit()
        logger.info(f"BULK UPDATE SUCCESS: Applied {discount_percent}% discount to {updated_count} products in '{category}'.")
    except Exception as e:
        session.rollback()
        logger.error(f"BULK UPDATE FAILED for category '{category}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during bulk update."
        )

    return {
        "message": "Bulk update successful",
        "category": category,
        "discount_applied_percent": discount_percent,
        "products_updated": updated_count
    }

# STOCK ADJUSTMENT (Must be above dynamic '{product_id}' routes)
@app.patch("/products/adjust-stock", tags=["Products"])
def adjust_stock(
    adjustments: List[StockAdjustment],
    session: Session = Depends(get_db)
):
    successful_updates = []
    failed_updates = []

    for adj in adjustments:
        product = session.get(Product, adj.product_id)
        if not product:
            failed_updates.append({
                "product_id": adj.product_id,
                "quantity_to_add": adj.quantity_to_add,
                "reason": "Product not found"
            })
            continue

        current_stock = product.stock
        new_stock = current_stock + adj.quantity_to_add

        if new_stock > 5000:
            failed_updates.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "current_stock": current_stock,
                "quantity_requested": adj.quantity_to_add,
                "reason": f"New stock ({new_stock}) exceeds the 5,000 unit warehouse capacity limit."
            })
            continue

        product.stock = new_stock
        product.updated_at = datetime.utcnow()
        session.add(product)
        
        successful_updates.append({
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "previous_stock": current_stock,
            "added": adj.quantity_to_add,
            "new_stock": new_stock
        })

    try:
        session.commit()
        logger.info(f"STOCK ADJUSTMENT: {len(successful_updates)} succeeded, {len(failed_updates)} failed.")
    except Exception as e:
        session.rollback()
        logger.error(f"Stock adjustment transaction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during stock adjustment."
        )

    return {
        "message": "Stock adjustment processed",
        "total_processed": len(adjustments),
        "successful_count": len(successful_updates),
        "failed_count": len(failed_updates),
        "successful_updates": successful_updates,
        "failed_updates": failed_updates
    }

# READ Single Product
@app.get("/products/{product_id}", response_model=ProductRead, tags=["Products"])
def read_product(product_id: int, session: Session = Depends(get_db)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

# UPDATE Product
@app.patch("/products/{product_id}", response_model=ProductRead, tags=["Products"])
def update_product(product_id: int, product_in: ProductUpdate, session: Session = Depends(get_db)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
        
    db_product.updated_at = datetime.utcnow()
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


# ==========================================
# Supplier Endpoints
# ==========================================

@app.post("/suppliers/", response_model=SupplierRead, status_code=status.HTTP_201_CREATED, tags=["Suppliers"])
def create_supplier(supplier_in: SupplierCreate, session: Session = Depends(get_db)):
    existing = session.exec(
        select(Supplier).where(
            (Supplier.email == supplier_in.email) | (Supplier.name == supplier_in.name)
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A supplier with this name or email already exists."
        )
        
    supplier = Supplier.model_validate(supplier_in)
    session.add(supplier)
    session.commit()
    session.refresh(supplier)
    return supplier


@app.get("/suppliers/", response_model=List[SupplierRead], tags=["Suppliers"])
def list_suppliers(
    skip: int = 0, 
    limit: int = 100, 
    is_active: Optional[bool] = None, 
    session: Session = Depends(get_db)
):
    query = select(Supplier)
    if is_active is not None:
        query = query.where(Supplier.is_active == is_active)
    
    suppliers = session.exec(query.offset(skip).limit(limit)).all()
    return suppliers


@app.patch("/suppliers/{supplier_id}", response_model=SupplierRead, tags=["Suppliers"])
def update_supplier(
    supplier_id: int, 
    supplier_in: SupplierUpdate, 
    session: Session = Depends(get_db)
):
    supplier = session.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        
    update_data = supplier_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)
        
    session.add(supplier)
    session.commit()
    session.refresh(supplier)
    return supplier