from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    industry: Literal["bank", "nbfc", "insurance", "fintech"]


class TenantOut(BaseModel):
    id: UUID
    name: str
    industry: str


class UserCreate(BaseModel):
    email: str
    full_name: str


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str


class CustomerCreate(BaseModel):
    display_name: str
    customer_type: Literal["individual", "entity"]
    country: str
    external_ref: str | None = None


class CustomerOut(BaseModel):
    id: UUID
    display_name: str
    customer_type: str
    country: str
    onboarding_status: str


class KycCaseCreate(BaseModel):
    customer_id: UUID
    case_type: Literal["onboarding", "periodic_review", "edd", "remediation"]


class KycCaseOut(BaseModel):
    id: UUID
    customer_id: UUID
    case_type: str
    status: str
    risk_tier: str | None
    ai_recommendation: dict | None
    decision: str | None
    decision_rationale: str | None


class AiRecommendationOut(BaseModel):
    case_id: UUID
    recommendation: dict
    requires_human_approval: bool = True


class DecisionCreate(BaseModel):
    approver_id: UUID
    decision: Literal["approved", "rejected", "escalated"]
    rationale: str
