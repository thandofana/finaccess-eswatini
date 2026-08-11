"""Strict request and response contracts for the assessment API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Gender = Literal["Female", "Male"]
AgeGroup = Literal["15–24", "25–34", "35–44", "45–54", "55–64", "65+"]
Education = Literal[
    "Missing or nonresponse",
    "Primary education or less",
    "Secondary education",
    "Tertiary education or more",
]
IncomeQuintile = Literal[
    "Income quintile 1",
    "Income quintile 2",
    "Income quintile 3",
    "Income quintile 4",
    "Income quintile 5",
]
WorkforceStatus = Literal["In the workforce", "Out of the workforce"]
YesNoNonresponse = Literal["Yes", "No", "Nonresponse"]
RecentInternetUse = Literal["Yes", "No / don't know / refused"]
PhoneAccessTier = Literal[
    "Smartphone",
    "Basic text phone",
    "No personal mobile phone",
    "Phone ownership nonresponse",
    "Phone type nonresponse",
]
RoutedYesNo = Literal["Yes", "No", "Nonresponse", "Not applicable / skipped"]
PhoneUseFrequency = Literal[
    "Daily",
    "Weekly",
    "Monthly",
    "Less than once a month",
    "Never",
    "Nonresponse",
    "Not applicable / skipped",
]
InternetEngagement = Literal[
    "Daily internet use",
    "Weekly internet use",
    "Monthly internet use",
    "Less than monthly internet use",
    "Recent-use indicator; frequency reported never",
    "Recent internet use; frequency nonresponse",
    "No recent internet use / no-DK-ref",
]
DataPurchasePattern = Literal[
    "Purchases data daily",
    "Purchases data weekly",
    "Purchases data monthly",
    "Purchases data less than monthly",
    "Reports purchasing data but frequency never",
    "Data-purchase frequency nonresponse",
    "Does not purchase data",
    "Data-purchase status nonresponse",
    "No recent internet use / skipped",
]


class AssessmentRequest(BaseModel):
    """One profile containing the union of both validated model inputs."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "female": "Female",
                    "age_group": "65+",
                    "educ": "Primary education or less",
                    "inc_q": "Income quintile 2",
                    "emp_in": "Out of the workforce",
                    "fin24c": "Yes",
                    "internet_use": "No / don't know / refused",
                    "internet_engagement_level": "No recent internet use / no-DK-ref",
                    "phone_access_tier": "Smartphone",
                    "con11": "Yes",
                    "con12": "Daily",
                    "con14": "Yes",
                    "con16": "Yes",
                    "con18": "No",
                    "con20": "No",
                    "data_purchase_pattern": "No recent internet use / skipped",
                    "fin46": "Yes",
                }
            ]
        },
    )

    female: Gender = Field(description="Respondent gender category used by both models.")
    age_group: AgeGroup = Field(description="Fixed leakage-safe age band.")
    educ: Education = Field(description="Highest completed education category.")
    inc_q: IncomeQuintile = Field(description="Within-economy household income quintile.")
    emp_in: WorkforceStatus = Field(description="Whether the person is in the workforce.")
    fin24c: YesNoNonresponse = Field(description="Natural-disaster or severe-weather experience.")
    internet_use: RecentInternetUse = Field(description="Internet use within the past three months.")
    internet_engagement_level: InternetEngagement = Field(description="Frequency-aware recent internet-use category.")
    phone_access_tier: PhoneAccessTier = Field(description="Personal phone ownership/type category.")
    con11: RoutedYesNo = Field(description="Whether the SIM is registered in the person's own name.")
    con12: PhoneUseFrequency = Field(description="Mobile-phone use frequency.")
    con14: RoutedYesNo = Field(description="Whether the person can read a text message.")
    con16: RoutedYesNo = Field(description="Whether the person can send a text message.")
    con18: RoutedYesNo = Field(description="Whether the phone has a PIN or password.")
    con20: RoutedYesNo = Field(description="Whether someone sets rules on the person's phone use.")
    data_purchase_pattern: DataPurchasePattern = Field(description="Internet data-purchase status and frequency.")
    fin46: YesNoNonresponse = Field(description="Foundational ID ownership.")

    @model_validator(mode="after")
    def validate_routing_consistency(self) -> "AssessmentRequest":
        no_recent_engagement = "No recent internet use / no-DK-ref"
        no_recent_purchase = "No recent internet use / skipped"
        if self.internet_use == "No / don't know / refused":
            if self.internet_engagement_level != no_recent_engagement:
                raise ValueError(
                    "internet_engagement_level must indicate no recent internet use when internet_use is No / don't know / refused."
                )
            if self.data_purchase_pattern != no_recent_purchase:
                raise ValueError(
                    "data_purchase_pattern must indicate no recent internet use when internet_use is No / don't know / refused."
                )
        else:
            if self.internet_engagement_level == no_recent_engagement:
                raise ValueError(
                    "internet_engagement_level cannot indicate no recent internet use when internet_use is Yes."
                )
            if self.data_purchase_pattern == no_recent_purchase:
                raise ValueError(
                    "data_purchase_pattern cannot indicate no recent internet use when internet_use is Yes."
                )

        routed_phone_fields = (self.con11, self.con12, self.con14, self.con16, self.con18, self.con20)
        if self.phone_access_tier == "No personal mobile phone" and any(
            value != "Not applicable / skipped" for value in routed_phone_fields
        ):
            raise ValueError(
                "Phone-routed fields must be Not applicable / skipped when phone_access_tier is No personal mobile phone."
            )
        return self


class ExplanationFactor(BaseModel):
    feature: str
    label: str
    value: str
    direction: Literal["increased_likelihood", "reduced_likelihood", "neutral"]
    explanation: str
    contribution_log_odds: float = Field(description="Signed SHAP contribution on the model log-odds scale.")


class PredictionResult(BaseModel):
    model: Literal["financial_inclusion", "mobile_money_adoption"]
    question: str
    answer: str
    probability: float = Field(ge=0, le=1)
    probability_percent: float = Field(ge=0, le=100)
    threshold: float = Field(ge=0, le=1)
    threshold_status: Literal["provisional"]
    baseline_probability: float = Field(ge=0, le=1)
    main_factors: list[ExplanationFactor] = Field(min_length=1, max_length=5)
    warnings: list[str]


class AssessmentResponse(BaseModel):
    assessment_id: str
    purpose: str
    financial_inclusion: PredictionResult
    mobile_money_adoption: PredictionResult
    disclaimer: str


class ModelHealth(BaseModel):
    model: str
    target: str
    status: Literal["ready"]
    pipeline_sha256: str
    explainer_sha256: str


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str
    models: list[ModelHealth]


class ErrorDetail(BaseModel):
    field: str
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
