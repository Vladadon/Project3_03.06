from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import ForeignKey, Table, Index, Integer, String, Column, Text, \
                       DateTime, Boolean, PrimaryKeyConstraint, \
                       UniqueConstraint, ForeignKeyConstraint, \
                       create_engine, MetaData, Float, Date
from calendar import monthrange
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError

# Создание объекта FastAPI
app = FastAPI()

# Настройка базы данных MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://isp_p_Golubin:12345@192.168.25.23/isp_p_Golubin"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Определение модели SQLAlchemy для пользователя

class Departments(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    department_name = Column(String(50))
    manager_name = Column(String(50))
    phone_number = Column(String(50))
    daily_sales_volume = Column(Float)

class Products(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    product_code = Column(String(50))
    product_name = Column(String(50))
    unit_of_measurement = Column(String(50))
    retail_price = Column(Float)

class Sales(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False, index=True)
    sale_date = Column(Date)
    quantity_sold = Column(Integer)

    product = relationship("Products")
    department = relationship("Departments")

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Создать запрос для вывода списка всех отделов;
@app.get("/departments/")
async def read_departments(skip: int = 0, limit: int = 100):
    departments = SessionLocal().query(Departments).offset(skip).limit(limit).all()
    return departments

# Создать запрос для вывода списка всех товаров;
@app.get("/products/")
async def read_products(skip: int = 0, limit: int = 100):
    products = SessionLocal().query(Products).offset(skip).limit(limit).all()
    return products

# Создать запрос для вывода списка всех продаж;
@app.get("/sales/")
async def read_sales(skip: int = 0, limit: int = 100):
    sales = SessionLocal().query(Sales).offset(skip).limit(limit).all()
    return sales

# Создать запрос для вывода списка всех продаж конкретного отдела;
@app.get("/sales/departments/{department_id}")
async def read_department_sales(department_id: int, skip: int = 0, limit: int = 100):
    sales = SessionLocal().query(Sales).filter(Sales.department_id == department_id).offset(skip).limit(limit).all()
    return sales

# Создать запрос для вывода списка всех продаж конкретного товара;
@app.get("/sales/products/{product_id}")
async def read_product_sales(product_id: int, skip: int = 0, limit: int = 100):
    sales = SessionLocal().query(Sales).filter(Sales.product_id == product_id).offset(skip).limit(limit).all()
    return sales

# Создать запрос для вывода общего количества проданного товара за все время;
from sqlalchemy.sql import func

@app.get("/total_quantity_sold")
async def total_quantity_sold():
    total = SessionLocal().query(func.sum(Sales.quantity_sold)).scalar()
    return {"Total Quantity Sold": total}

# Создать запрос для вывода общей суммы выручки от продаж за все время;
@app.get("/total_revenue")
async def total_revenue():
    total = SessionLocal().query(func.sum(Sales.quantity_sold * Products.retail_price)).scalar()
    return {"Total Revenue": total}

# Создать запрос для вывода средней цены продажи конкретного товара;
@app.get("/average_sale_price/{product_id}")
async def average_sale_price(product_id: int):
    avg_price = SessionLocal().query(func.avg(Sales.quantity_sold * Products.retail_price)).filter(Sales.product_id == product_id).scalar()
    return {"Average Sale Price": avg_price}

# Создать запрос для вывода списка отделов, объем реализации в день которых превышает заданную сумму;
@app.get("/departments/sales_exceeding/{threshold}")
async def departments_with_high_sales(threshold: float):
    result = SessionLocal().query(
        Departments,
        func.sum(Sales.quantity_sold * Products.retail_price).label('daily_revenue')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).group_by(
        Departments.id, Departments.department_name
    ).having(
        func.sum(Sales.quantity_sold * Products.retail_price) > threshold
    ).all()
    return result

# Создать запрос для вывода списка товаров, розничная цена которых больше заданной суммы;
@app.get("/products/above_price/{price_threshold}")
async def products_above_price(price_threshold: float):
    result = SessionLocal().query(Products).filter(Products.retail_price > price_threshold).all()
    return result

# Создать запрос для вывода списка отделов и соответствующей им общей суммы выручки от продаж за заданный период времени. Отображение отделов и их объема реализации в день.
@app.get("/departments/revenue_period/{start_date}/{end_date}")
async def department_revenue(start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    result = SessionLocal().query(
        Departments,
        func.sum(Sales.quantity_sold * Products.retail_price).label('revenue')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).filter(
        Sales.sale_date.between(start_date, end_date)
    ).group_by(
        Departments.id, Departments.department_name
    ).all()
    return result

# Отображение товаров, которые были проданы за определенный период времени.
@app.get("/products/sold_in_period/{start_date}/{end_date}")
async def products_sold_in_period(start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    result = SessionLocal().query(Products).join(
        Sales, Sales.product_id == Products.id
    ).filter(
        Sales.sale_date.between(start_date, end_date)
    ).distinct().all()
    return result

# Расчет общей суммы продаж для каждого отдела за определенный период времени.
@app.get("/departments/total_sales_period/{start_date}/{end_date}")
async def department_total_sales(start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    result = SessionLocal().query(
        Departments,
        func.sum(Sales.quantity_sold * Products.retail_price).label('total_sales')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).filter(
        Sales.sale_date.between(start_date, end_date)
    ).group_by(
        Departments.id, Departments.department_name
    ).all()
    return result

# Определение топ-10 самых продаваемых товаров.
@app.get("/top_selling_products")
async def top_selling_products():
    result = SessionLocal().query(
        Products,
        func.sum(Sales.quantity_sold).label('quantity_sold')
    ).join(
        Sales, Sales.product_id == Products.id
    ).group_by(
        Products.id, Products.product_name
    ).order_by(
        func.sum(Sales.quantity_sold).desc()
    ).limit(10).all()
    return result

# Расчет среднего чека в каждом отделе за месяц.
@app.get("/departments/avg_check_size_month/{year}/{month}")
async def avg_check_size_per_department(year: int, month: int):
    days_in_month = monthrange(year, month)[1]
    result = SessionLocal().query(
        Departments,
        func.avg(Sales.quantity_sold * Products.retail_price).label('avg_check_size')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).filter(
        func.extract('MONTH', Sales.sale_date) == month,
        func.extract('YEAR', Sales.sale_date) == year
    ).group_by(
        Departments.id, Departments.department_name
    ).all()
    return result

# Отображение товаров с ценой, превышающей определенный порог.
@app.get("/products/prices_above/{price_threshold}")
async def products_prices_above(price_threshold: float):
    result = SessionLocal().query(Products).filter(Products.retail_price > price_threshold).all()
    return result

# Расчет прибыли от продаж для каждого отдела за год.
@app.get("/departments/profit_year/{year}")
async def department_profit_per_year(year: int):
    result = SessionLocal().query(
        Departments,
        func.sum(Sales.quantity_sold * (Products.retail_price - Products.cost_price)).label('profit')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).filter(
        func.extract('YEAR', Sales.sale_date) == year
    ).group_by(
        Departments.id, Departments.department_name
    ).all()
    return result

# Определение даты, когда были проданы наибольшее количество товаров.
@app.get("/highest_sales_date")
async def highest_sales_date():
    result = SessionLocal().query(
        func.max(Sales.quantity_sold).label('max_sales'),
        func.date_trunc('day', Sales.sale_date).label('sale_date')
    ).group_by(
        func.date_trunc('day', Sales.sale_date)
    ).order_by(
        func.max(Sales.quantity_sold).desc()
    ).first()
    return result

# Запрос на выборку отделов с наибольшей выручкой за выбранный период времени, с указанием объема реализации и количества проданных товаров в каждом отделе.
@app.get("/departments/highest_revenue/{start_date}/{end_date}")
async def highest_revenue_departments(start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    result = SessionLocal().query(
        Departments,
        func.sum(Sales.quantity_sold * Products.retail_price).label('total_revenue'),
        func.count(Sales.id).label('items_sold_count')
    ).join(
        Sales, Sales.department_id == Departments.id
    ).join(
        Products, Products.id == Sales.product_id
    ).filter(
        Sales.sale_date.between(start_date, end_date)
    ).group_by(
        Departments.id, Departments.department_name
    ).order_by(
        func.sum(Sales.quantity_sold * Products.retail_price).desc()
    ).all()
    
    return result

# Составление отчета о наиболее продаваемых товарах за определенный период времени, с указанием количества продаж каждого товара и их доли в общем объеме продаж.
@app.get("/products/most_sold/{start_date}/{end_date}")
async def most_sold_products(start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    total_sales_volume = SessionLocal().query(func.sum(Sales.quantity_sold * Products.retail_price)).\
        filter(Sales.sale_date.between(start_date, end_date)).scalar() or 1
    
    result = SessionLocal().query(
        Products,
        func.sum(Sales.quantity_sold).label('sales_count'),
        (func.sum(Sales.quantity_sold) / total_sales_volume * 100).label('share_of_total_sales')
    ).join(
        Sales, Sales.product_id == Products.id
    ).filter(
        Sales.sale_date.between(start_date, end_date)
    ).group_by(
        Products.id, Products.product_name
    ).order_by(
        func.sum(Sales.quantity_sold).desc()
    ).all()
    
    return result

# Создание отчета о наиболее выбивающихся продажах (по объему продаж), с указанием даты, отдела и товара.
@app.get("/outstanding_sales/by_volume")
async def outstanding_sales_by_volume():
    result = SessionLocal().query(
        Sales.sale_date.label('date'),
        Departments.department_name.label('department'),
        Products.product_name.label('product'),
        func.sum(Sales.quantity_sold * Products.retail_price).label('sales_volume')
    ).join(
        Departments, Departments.id == Sales.department_id
    ).join(
        Products, Products.id == Sales.product_id
    ).group_by(
        Sales.sale_date, Departments.department_name, Products.product_name
    ).order_by(
        func.sum(Sales.quantity_sold * Products.retail_price).desc()
    ).first()
    
    return result




# # Определение Pydantic модели для пользователя
# class UserCreate(BaseModel):
#     name: str
#     email: str

# class UserResponse(BaseModel):
#     id: int
#     name: str
#     email: str

#     class Config:
#         orm_mode = True

# # Зависимость для получения сессии базы данных
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Маршрут для получения пользователя по ID
# @app.get("/users/{user_id}", response_model=UserResponse)
# def read_user(user_id: int, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user

# # Маршрут для создания нового пользователя
# @app.post("/users/", response_model=UserResponse)
# def create_user(user: UserCreate, db: Session = Depends(get_db)):
#     db_user = User(name=user.name, email=user.email)
#     try:
#         db.add(db_user)
#         db.commit()
#         db.refresh(db_user)
#         return db_user
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=400, detail="Email already registered")