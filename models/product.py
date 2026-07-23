import re
from datetime import datetime
from typing import Optional, List
from pydantic import field_validator, ValidationInfo
from sqlmodel import SQLModel, Field, Relationship

# ==========================================
# 1. Database Table Models
# ==========================================

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    
    products: List["Product"] = Relationship(back_populates="category_rel")


class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    contact_person: str
    email: str = Field(unique=True, index=True)
    phone: str
    is_active: bool = Field(default=True)
    
    products: List["Product"] = Relationship(back_populates="supplier")


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    brand: str
    category: str
    price: float
    sku: str = Field(index=True, unique=True)
    warranty_months: int
    stock: int = Field(ge=0, le=10000, default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category_rel: Optional[Category] = Relationship(back_populates="products")
    
    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id")
    supplier: Optional[Supplier] = Relationship(back_populates="products")


# ==========================================
# 2. Reusable Validation Logic
# ==========================================

def shared_validate_name(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("Product name must contain at least one word")
    if not v[0].isupper():
        raise ValueError("Product name must start with a capital letter")
    if not re.match(r"^[A-Za-z0-9\s\-]+$", v):
        raise ValueError("Product name cannot contain special characters (except spaces and hyphens)")
    return v

def shared_validate_brand(v: str) -> str:
    allowed_brands = ["HP", "Dell", "Lenovo", "Apple", "Samsung", "Intel", "AMD", "Corsair", "Logitech", "Other"]
    upper_v = v.strip().upper()
    
    standardized_input = upper_v if upper_v in ["HP", "AMD", "Intel"] else v.strip().title()
    
    for brand in allowed_brands:
        if standardized_input.upper() == brand.upper():
            return brand
    raise ValueError(f"Brand must be from the allowed list: {allowed_brands}")

def shared_validate_category(v: str) -> str:
    allowed_categories = ["Laptops", "Monitors", "Storage", "Processors", "Memory", "Keyboards", "Mice", "Accessories"]
    for cat in allowed_categories:
        if v.strip().lower() == cat.lower():
            return cat
    raise ValueError(f"Category must be one of: {allowed_categories}")

def shared_validate_price(v: float) -> float:
    if not float(v).is_integer() and len(str(v).split(".")[1]) > 2:
        raise ValueError("Price must have at most 2 decimal places")
        
    if v < 100:
        raise ValueError("Price cannot be too low (minimum 100 KSh for any product)")
        
    if v > 500000:
        raise ValueError("Price cannot be unrealistically high (max 500,000 KSh)")
        
    return round(v, 2)

def shared_validate_sku(v: str) -> str:
    if not re.match(r"^[A-Z]{3,4}-[A-Z]{2,4}-[0-9]{4}$", v):
        raise ValueError("SKU must match the format: CAT-BRAND-XXXX (e.g., LAP-HP-0001)")
    
    prefix = v.split("-")[0]
    valid_abbreviations = ["LAP", "MON", "STO", "PRO", "MEM", "KEY", "MOU", "ACC"]
    if prefix not in valid_abbreviations:
        raise ValueError(f"Category abbreviation part must be one of {valid_abbreviations}")
    return v

def shared_validate_warranty(v: int, info: ValidationInfo) -> int:
    if v < 0 or v > 36:
        raise ValueError("Warranty must be between 0 and 36 months")
    
    price = info.data.get("price")
    if price is not None and price > 50000 and v < 12:
        raise ValueError("If price is greater than 50,000 KSh, warranty must be at least 12 months")
    return v

def shared_validate_email(v: str) -> str:
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
        raise ValueError("Invalid email address format")
    return v.lower()

def shared_validate_phone(v: str) -> str:
    cleaned = v.replace(" ", "")
    if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
        raise ValueError("Phone number must contain 7 to 15 digits and may start with a '+'")
    return cleaned


# ==========================================
# 3. API Schema / Validation Models
# ==========================================

class ProductCreate(SQLModel):
    name: str
    description: str = Field(min_length=15) 
    brand: str
    category: str
    price: float
    stock: Optional[int] = Field(default=0, ge=0) 
    warranty_months: int
    sku: str
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None

    _validate_name = field_validator("name")(shared_validate_name)
    _validate_brand = field_validator("brand")(shared_validate_brand)
    _validate_category = field_validator("category")(shared_validate_category)
    _validate_price = field_validator("price")(shared_validate_price)
    _validate_sku = field_validator("sku")(shared_validate_sku)
    
    @field_validator("warranty_months")
    @classmethod
    def validate_warranty(cls, v: int, info: ValidationInfo) -> int:
        return shared_validate_warranty(v, info)


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    sku: Optional[str] = None
    warranty_months: Optional[int] = None
    stock: Optional[int] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None

    @field_validator("name", "brand", "category", "sku", mode="before")
    @classmethod
    def check_optionals_strings(cls, v):
        return v if v is None else v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return shared_validate_name(v) if v is not None else v

    @field_validator("brand")
    @classmethod
    def validate_brand(cls, v):
        return shared_validate_brand(v) if v is not None else v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        return shared_validate_category(v) if v is not None else v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        return shared_validate_price(v) if v is not None else v

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):
        return shared_validate_sku(v) if v is not None else v

    @field_validator("warranty_months")
    @classmethod
    def validate_warranty(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        if v is not None:
            return shared_validate_warranty(v, info)
        return v


class ProductRead(SQLModel):
    id: int
    name: str
    brand: str
    category: str
    price: float
    sku: str
    warranty_months: int
    stock: int
    category_id: Optional[int]
    supplier_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class StockAdjustment(SQLModel):
    product_id: int
    quantity_to_add: int = Field(gt=0)


class SupplierCreate(SQLModel):
    name: str
    contact_person: str
    email: str
    phone: str
    is_active: Optional[bool] = True

    _validate_email = field_validator("email")(shared_validate_email)
    _validate_phone = field_validator("phone")(shared_validate_phone)


class SupplierRead(SQLModel):
    id: int
    name: str
    contact_person: str
    email: str
    phone: str
    is_active: bool


class SupplierUpdate(SQLModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return shared_validate_email(v)
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return shared_validate_phone(v)
        return v