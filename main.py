from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Table, Index, Integer, String, Column, Text, \
                       DateTime, Boolean, PrimaryKeyConstraint, \
                       UniqueConstraint, ForeignKeyConstraint, \
                       create_engine, MetaData, Float, Date
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
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

    department_id = Column(Integer, primary_key=True, nullable=True, index=True)
    department_name = Column(String(50))
    manager_name = Column(String(50))
    phone_number = Column(String(50))
    daily_sales_volume = Column(Float)

class Products(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, nullable=True, index=True)
    product_code = Column(String(50))
    product_name = Column(String(50))
    unit_of_measurement = Column(String(50))
    retail_price = Column(Float)

class Sales(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, nullable=True, index=True)
    product_id = Column(Integer, primary_key=True, nullable=True, index=True)
    department_id = Column(Integer, primary_key=True, nullable=True, index=True)
    sale_date = Column(Date)
    quantity_sold = Column(Integer)

    product = relationship("Products")
    department = relationship("Departments")

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Определение Pydantic модели для пользователя
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        orm_mode = True

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Маршрут для получения пользователя по ID
@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Маршрут для создания нового пользователя
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(name=user.name, email=user.email)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")