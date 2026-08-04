from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models._base import Role
from app.schemas.employees import EmployeeCreate, EmployeeOut


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    is_active: bool
    mfa_enabled: bool = False
    created_at: datetime


class TwoFactorSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TwoFactorEnableIn(BaseModel):
    code: str = Field(min_length=1, max_length=16)


class TwoFactorEnableOut(BaseModel):
    recovery_codes: list[str]


class TwoFactorDisableIn(BaseModel):
    password: str


class MeOut(BaseModel):
    user: UserOut
    employee: EmployeeOut | None = None


class MeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class InviteIn(BaseModel):
    email: EmailStr
    role: Role = Role.employee
    initial_employee: EmployeeCreate


class InviteOut(BaseModel):
    user_id: int
    email: EmailStr
    role: Role
    # Only populated when EMAIL_PROVIDER=console, so dev can grab the link.
    invite_link: str | None = None


class UserAdminUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
