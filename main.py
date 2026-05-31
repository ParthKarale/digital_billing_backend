from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List
import os
from fpdf import FPDF
from pydantic import BaseModel
from passlib.context import CryptContext

import models
import schemas
import database

# This is the tool that scrambles passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

models.Base.metadata.create_all(bind=database.engine)

# Smart Auto-Updater
# Each command gets its own transaction so one failure doesn't block the others!

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE invoice ADD COLUMN discount_percent NUMERIC(5,2) DEFAULT 0;"))
except: pass

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE invoice ADD COLUMN cgst_percent NUMERIC(5,2) DEFAULT 0;"))
except: pass

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE invoice ADD COLUMN sgst_percent NUMERIC(5,2) DEFAULT 0;"))
except: pass

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE customer ADD COLUMN address TEXT NOT NULL DEFAULT 'Not Provided';"))
except: pass

# --- OWNER TABLE UPDATES ---
try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE owners ADD COLUMN company_name VARCHAR;"))
except: pass

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE owners ADD COLUMN company_phone VARCHAR;"))
except: pass

try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE owners ADD COLUMN company_address VARCHAR;"))
except: pass
class OwnerSignupReq(BaseModel):
    email: str
    password: str
    companyName: str
    companyPhone: str
    companyAddress: str

class OwnerLoginReq(BaseModel):
    email: str
    password: str

class EmployeeActivateReq(BaseModel):
    employeeName: str
    employeeKey: str

class EmployeeLoginReq(BaseModel):
    employeeKey: str

class EmployeeCreateReq(BaseModel):
    access_key: str

os.makedirs("receipts", exist_ok=True)
app = FastAPI(title="Digital Billing System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], # ALLOWS ANY WEBSITE TO CONNECT
    allow_credentials=False, # MUST BE FALSE WHEN ORIGINS IS "*"
    allow_methods=["*"], 
    allow_headers=["*"],
)
app.mount("/receipts", StaticFiles(directory="receipts"), name="receipts")

@app.get("/")
def health_check(): return {"message": "Digital Billing Backend is Running!"}

# --- CUSTOMERS & PRODUCTS ---
@app.post("/product/", response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    # 1. Look for an existing product with the same name (ignoring uppercase/lowercase) and same price
    existing_product = db.query(models.Product).filter(
        models.Product.name.ilike(product.name),
        models.Product.price == product.price
    ).first()

    if existing_product:
        # 2. RESTOCK: If it exists, just add the new stock to the existing stock!
        existing_product.stock_quantity += product.stock_quantity
        db.commit()
        db.refresh(existing_product)
        return existing_product
    else:
        # 3. CREATE NEW: If it does not exist, create a brand new row
        new_prod = models.Product(**product.model_dump())
        db.add(new_prod)
        db.commit()
        db.refresh(new_prod)
        return new_prod

@app.get("/customer/", response_model=List[schemas.CustomerResponse])
def get_all_customers(db: Session = Depends(database.get_db)): return db.query(models.Customer).all()

@app.get("/product/", response_model=List[schemas.ProductResponse])
def get_inventory(db: Session = Depends(database.get_db)): return db.query(models.Product).all()

@app.get("/invoice/", response_model=List[schemas.InvoiceResponse])
def get_all_invoices(db: Session = Depends(database.get_db)): return db.query(models.Invoice).all()

# --- SYNCHRONOUS INVOICE & PDF GENERATION ---
@app.post("/invoice/", response_model=schemas.InvoiceResponse)
def create_invoice(invoice: schemas.InvoiceCreate, db: Session = Depends(database.get_db)):
    # 1. Save Header
    new_invoice = models.Invoice(
        customer_id=invoice.customer_id, amount=invoice.amount,
        discount_percent=invoice.discount_percent, cgst_percent=invoice.cgst_percent,
        sgst_percent=invoice.sgst_percent, status="Completed", local_file_path="" 
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # 2. Setup PDF
    pdf = FPDF()
    pdf.add_page()
    customer = db.query(models.Customer).filter(models.Customer.customer_id == invoice.customer_id).first()
    
    # Header
    pdf.set_font("Arial", style="B", size=22)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, txt="YOUR COMPANY NAME", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, txt="123 Business Avenue, Tech Park, City Name, State 411001", ln=True, align='C')
    pdf.cell(0, 5, txt="Phone: +91-9876543210  |  Email: contact@yourcompany.com", ln=True, align='C')
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Customer Details
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(100, 6, txt="BILL TO:", ln=False)
    pdf.cell(90, 6, txt="INVOICE DETAILS:", ln=True, align='R')
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 6, txt=f"Name: {customer.full_name}", ln=False)
    pdf.cell(90, 6, txt=f"Invoice No: #{new_invoice.invoice_id}", ln=True, align='R')
    pdf.cell(100, 6, txt=f"Phone: {customer.phone_number}", ln=False)
    pdf.cell(90, 6, txt=f"Date: {new_invoice.created_at.strftime('%Y-%m-%d')}", ln=True, align='R')
    pdf.cell(100, 6, txt=f"Address: {customer.address}", ln=False)
    pdf.ln(6)
    if customer.email: pdf.cell(100, 6, txt=f"Email: {customer.email}", ln=True)
    pdf.ln(5)

    # Table Headers
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", style="B", size=10)
    pdf.cell(15, 10, txt="S.No", border=1, align='C', fill=True)
    pdf.cell(85, 10, txt=" Items", border=1, fill=True)
    pdf.cell(25, 10, txt="Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, txt="Rate", border=1, align='R', fill=True)
    pdf.cell(35, 10, txt="Cost", border=1, align='R', fill=True)
    pdf.ln(10)

    # Table Rows & Inventory Deduction
    pdf.set_font("Arial", size=10)
    subtotal = 0
    for i, item in enumerate(invoice.items, 1):
        new_item = models.InvoiceItem(invoice_id=new_invoice.invoice_id, **item.model_dump())
        db.add(new_item)
        product = db.query(models.Product).filter(models.Product.product_id == item.product_id).first()
        if product:
            product.stock_quantity -= item.quantity 
            pdf.cell(15, 10, txt=str(i), border=1, align='C')
            pdf.cell(85, 10, txt=f" {product.name}", border=1)
            pdf.cell(25, 10, txt=str(item.quantity), border=1, align='C')
            pdf.cell(30, 10, txt=f"Rs. {item.unit_price:.2f} ", border=1, align='R')
            pdf.cell(35, 10, txt=f"Rs. {item.total_price:.2f} ", border=1, align='R')
            pdf.ln(10)
            subtotal += float(item.total_price)
    
    # Math Breakdown
    pdf.ln(5)
    discount_amt = subtotal * (float(invoice.discount_percent) / 100)
    taxable_amt = subtotal - discount_amt
    cgst_amt = taxable_amt * (float(invoice.cgst_percent) / 100)
    sgst_amt = taxable_amt * (float(invoice.sgst_percent) / 100)

    pdf.set_x(100)
    pdf.cell(55, 8, txt="Subtotal:", align='R')
    pdf.cell(35, 8, txt=f"Rs. {subtotal:.2f}", align='R', ln=True)
    if invoice.discount_percent > 0:
        pdf.set_x(100)
        pdf.cell(55, 8, txt=f"Discount ({invoice.discount_percent}%):", align='R')
        pdf.cell(35, 8, txt=f"- Rs. {discount_amt:.2f}", align='R', ln=True)
    if invoice.cgst_percent > 0:
        pdf.set_x(100)
        pdf.cell(55, 8, txt=f"CGST ({invoice.cgst_percent}%):", align='R')
        pdf.cell(35, 8, txt=f"+ Rs. {cgst_amt:.2f}", align='R', ln=True)
    if invoice.sgst_percent > 0:
        pdf.set_x(100)
        pdf.cell(55, 8, txt=f"SGST ({invoice.sgst_percent}%):", align='R')
        pdf.cell(35, 8, txt=f"+ Rs. {sgst_amt:.2f}", align='R', ln=True)

    pdf.ln(2)
    pdf.set_x(100)
    pdf.set_font("Arial", style="B", size=13)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(55, 12, txt="GRAND TOTAL:", align='R', fill=True)
    pdf.cell(35, 12, txt=f"Rs. {invoice.amount:.2f} ", align='R', fill=True, ln=True)

    pdf.set_y(-35)
    pdf.set_font("Arial", style="B", size=10)
    pdf.set_text_color(220, 53, 69)
    pdf.cell(0, 6, txt="NOTICE: Working Hours: 9:00 AM to 8:00 PM | We are closed on Sundays.", align='C', ln=True)

    # Save PDF and return
    file_path = f"receipts/invoice_{new_invoice.invoice_id}.pdf"
    pdf.output(file_path)
    new_invoice.local_file_path = file_path
    db.commit()
    db.refresh(new_invoice)
    
    return new_invoice

# ==========================================
# 🛑 DELETE ENDPOINTS
# ==========================================
@app.delete("/customer/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.customer_id == customer_id).first()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    try:
        db.delete(customer)
        db.commit()
        return {"message": "Customer deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete! This customer is tied to an existing bill.")

@app.delete("/product/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    try:
        db.delete(product)
        db.commit()
        return {"message": "Product deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete! This product is on a past bill.")

@app.delete("/invoice/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(database.get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice: raise HTTPException(status_code=404, detail="Invoice not found")
    # Because we set cascade="all, delete" in models.py, deleting the invoice 
    # will automatically delete all its line items too!
    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted successfully"}

# ==========================================
# 📊 ANALYTICS DASHBOARD
# ==========================================
@app.get("/analytics/")
def get_analytics(db: Session = Depends(database.get_db)):
    # 1. Calculate Total Revenue
    total_revenue = db.query(func.sum(models.Invoice.amount)).scalar() or 0
    
    # 2. Count Total Bills
    total_bills = db.query(models.Invoice).count()
    
    # 3. Find Low Stock Items (Less than 10 left)
    low_stock = db.query(models.Product).filter(models.Product.stock_quantity <= 10).all()
    
    # 4. Get last 7 bills for the Bar Chart
    recent_invoices = db.query(models.Invoice).order_by(models.Invoice.created_at.desc()).limit(7).all()
    chart_data = [{"name": f"#{inv.invoice_id}", "revenue": float(inv.amount)} for inv in reversed(recent_invoices)]
    
    return {
        "total_revenue": float(total_revenue),
        "total_bills": total_bills,
        "low_stock_items": low_stock,
        "chart_data": chart_data
    }

# ==========================================
# 🔐 AUTHENTICATION ENDPOINTS (OWNER & EMPLOYEE)
# ==========================================

@app.post("/api/owner/signup")
def owner_signup(req: OwnerSignupReq, db: Session = Depends(database.get_db)):
    # 1. Check if email already exists
    existing_owner = db.query(models.Owner).filter(models.Owner.email == req.email).first()
    if existing_owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Hash the password and save the new owner
    hashed_pw = pwd_context.hash(req.password)
    new_owner = models.Owner(
        email=req.email,
        hashed_password=hashed_pw,
        company_name=req.companyName,
        company_phone=req.companyPhone,
        company_address=req.companyAddress
    )
    db.add(new_owner)
    db.commit()
    return {"message": "Owner created successfully!"}

@app.post("/api/owner/login")
def owner_login(req: OwnerLoginReq, db: Session = Depends(database.get_db)):
    owner = db.query(models.Owner).filter(models.Owner.email == req.email).first()
    
    # Check if owner exists AND password matches the scrambled hash
    if not owner or not pwd_context.verify(req.password, owner.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {"message": "Login successful", "role": "owner", "company": owner.company_name}


@app.post("/api/employee/activate")
def employee_activate(req: EmployeeActivateReq, db: Session = Depends(database.get_db)):
    # Find the blank 6-digit key the owner generated
    key_record = db.query(models.Employee).filter(models.Employee.access_key == req.employeeKey).first()
    
    if not key_record:
        raise HTTPException(status_code=404, detail="Invalid 6-digit key")
    if key_record.is_active:
        raise HTTPException(status_code=400, detail="This key has already been claimed")
        
    # Claim the key
    key_record.name = req.employeeName
    key_record.is_active = True
    db.commit()
    
    return {"message": "Employee activated successfully!"}

@app.post("/api/employee/login")
def employee_login(req: EmployeeLoginReq, db: Session = Depends(database.get_db)):
    employee = db.query(models.Employee).filter(models.Employee.access_key == req.employeeKey).first()
    
    if not employee or not employee.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive access key")
        
    return {"message": "Login successful", "role": "employee", "name": employee.name}

@app.post("/api/employee/create")
def create_employee_key(req: EmployeeCreateReq, db: Session = Depends(database.get_db)):
    # Create a blank, inactive employee slot
    new_emp = models.Employee(access_key=req.access_key, name="Unclaimed", is_active=False)
    db.add(new_emp)
    db.commit()
    return {"message": "Key generated successfully!"}