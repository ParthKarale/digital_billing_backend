from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# ==========================================
# CUSTOMER SCHEMAS
# ==========================================
class CustomerBase(BaseModel):
    full_name: str
    phone_number: str
    address: str    # <-- ADD THIS LINE
    email: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass # Waiter sends this (no ID yet)

class CustomerResponse(CustomerBase):
    customer_id: int
    created_at: datetime
    
    # This tells Pydantic to read data from SQLAlchemy models seamlessly
    model_config = ConfigDict(from_attributes=True) 


# ==========================================
# PRODUCT SCHEMAS
# ==========================================
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    stock_quantity: int = Field(default=0, ge=0) # ge=0 ensures stock cannot be negative

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    product_id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# INVOICE ITEM SCHEMAS
# ==========================================
class InvoiceItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0) # gt=0 ensures they buy at least 1
    unit_price: Decimal
    total_price: Decimal

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItemResponse(InvoiceItemBase):
    item_id: int
    invoice_id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# INVOICE SCHEMAS
# ==========================================
class InvoiceBase(BaseModel):
    customer_id: int
    amount: Decimal
    
    # --- ADD THESE 3 LINES ---
    discount_percent: Decimal = Decimal('0.0')
    cgst_percent: Decimal = Decimal('0.0')
    sgst_percent: Decimal = Decimal('0.0')
    # -------------------------
    
    status: str = "Pending"
    local_file_path: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    # When creating an invoice, we want to receive the items at the same time!
    items: List[InvoiceItemCreate]

class InvoiceResponse(InvoiceBase):
    invoice_id: int
    created_at: datetime
    items: List[InvoiceItemResponse] = [] # Sends back the line items nested inside the invoice

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PAYMENT SCHEMAS
# ==========================================
class PaymentBase(BaseModel):
    invoice_id: int
    amount_paid: Decimal
    payment_method: str
    transaction_reference: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    payment_id: int
    payment_date: datetime

    model_config = ConfigDict(from_attributes=True)