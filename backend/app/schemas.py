from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "researcher"
    research_interest: str = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = ""

class AIRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=5000)
