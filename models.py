from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    address = Column(Text, nullable=False, default="Not Provided") # <-- ADD THIS LINE
    email = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="customer")
class Product(Base):
    __tablename__ = "product"

    product_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)


class Invoice(Base):
    __tablename__ = "invoice"

    invoice_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id"))
    amount = Column(Numeric(10, 2), nullable=False)
    
    # --- ADD THESE 3 LINES ---
    discount_percent = Column(Numeric(5, 2), default=0)
    cgst_percent = Column(Numeric(5, 2), default=0)
    sgst_percent = Column(Numeric(5, 2), default=0)
    # -------------------------

    status = Column(String(50), default="Pending")
    local_file_path = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete")


class InvoiceItem(Base):
    __tablename__ = "invoice_item"

    item_id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoice.invoice_id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("product.product_id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payment"

    payment_id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoice.invoice_id", ondelete="CASCADE"))
    amount_paid = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    transaction_reference = Column(String(255))
    payment_date = Column(DateTime, default=datetime.utcnow)
 # Just in case this isn't imported at the top!

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Unclaimed")
    access_key = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=False)
class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    company_name = Column(String)
    company_phone = Column(String)
    company_address = Column(String)