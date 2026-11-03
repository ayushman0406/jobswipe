from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, LargeBinary, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    email: str = ""
    preferred_lang: str = "en"  # en | hi | kn
    resume_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    ats_score: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    resume_latex: Optional[str] = Field(default=None, sa_column=Column(Text))
    # {"filters": {...}, "focus": "english description"}
    search_state: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    resume_vec: Optional[bytes] = Field(default=None, sa_column=Column(LargeBinary))
    pref_vec: Optional[bytes] = Field(default=None, sa_column=Column(LargeBinary))  # learns from swipes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: Optional[int] = None  # job_provider side, later
    title: str
    company: str = ""
    location: str = ""
    remote: bool = False
    employment_type: str = "full-time"
    salary_min: Optional[int] = None   # annual, INR
    salary_max: Optional[int] = None
    currency: str = "INR"
    description: str = ""
    skills: list = Field(default_factory=list, sa_column=Column(JSON))
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None
    # Family of work. See app.catalog.CATEGORIES (sales, retail, mechanical, finance, healthcare, ...).
    category: str = ""
    industry: str = ""
    education: str = ""          # free text: "MBBS", "CA", "ITI", "12th", "Any graduate"
    shift: str = ""              # day | night | rotational | flexible
    languages: list = Field(default_factory=list, sa_column=Column(JSON))
    benefits: list = Field(default_factory=list, sa_column=Column(JSON))
    openings: int = 1
    status: str = "open"
    photo_url: Optional[str] = None
    company_logo: Optional[str] = None
    hiring_quote: Optional[str] = None
    vec: Optional[bytes] = Field(default=None, sa_column=Column(LargeBinary))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Swipe(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    job_id: int = Field(index=True)
    action: str  # like | pass | superlike
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    job_id: int = Field(index=True)
    status: str = "applied"  # applied -> mutual | rejected
    meet_url: Optional[str] = None
    next_steps: Optional[list] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))