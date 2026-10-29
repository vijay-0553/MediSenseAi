from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=0, le=130)
    sex: str = Field(..., min_length=1, max_length=20)
    contact: str = Field("", max_length=50)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, min_length=1, max_length=20)
    contact: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, min_length=3, max_length=255)

class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

class UserResponse(BaseModel):
    id: str
    name: str
    age: int
    sex: str
    contact: str
    email: str
    avatar_url: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
