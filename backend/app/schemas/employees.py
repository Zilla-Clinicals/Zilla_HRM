from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# active   = user is active and has accepted their invite
# pending  = invited but has not yet set a password / accepted
# inactive = was active, since deactivated by an admin
EmployeeStatus = Literal["active", "pending", "inactive"]

Gender = Literal["male", "female", "other", "prefer_not_to_say"]
MaritalStatus = Literal["single", "married", "divorced", "widowed"]
EmploymentType = Literal["full_time", "part_time", "contract", "intern"]


class EmployeeBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)

    # Personal
    date_of_birth: date | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    nationality: str | None = None
    personal_email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None

    # Employment
    employee_number: str | None = None
    job_title: str | None = None
    team: str | None = None
    employment_type: EmploymentType | None = None
    work_location: str | None = None
    hire_date: date | None = None
    manager_id: int | None = None

    # Emergency contact
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    """All fields optional; only provided fields are updated."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    date_of_birth: date | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    nationality: str | None = None
    personal_email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    employee_number: str | None = None
    job_title: str | None = None
    team: str | None = None
    employment_type: EmploymentType | None = None
    work_location: str | None = None
    hire_date: date | None = None
    manager_id: int | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool = True
    status: EmployeeStatus = "active"
    has_photo: bool = False
    created_at: datetime
    updated_at: datetime
