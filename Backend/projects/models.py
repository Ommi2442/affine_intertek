from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class TRFItem(BaseModel):
    TRF_No: str
    TRF_Date: str

class CDRItem(BaseModel):
    CDR_No: str
    CDR_Date: str

class LetterItem(BaseModel):
    Letter_No: str
    Letter_Date: str

class ProjectCreate(BaseModel):
    Standard: str
    Project_Id: str
    Proj_Created_By: str
    User_Name: str
    Client_Name: str
    Product: str



class ProjectProgress(BaseModel):
    # TRF
    trf_percentage: Optional[int] = 10
    trf_step: Optional[str] = None
    trf_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    trf_error: Optional[str] = None
    trf_completed: bool = False

    # CDR
    cdr_percentage: Optional[int] = 10
    cdr_step: Optional[str] = None
    cdr_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    cdr_error: Optional[str] = None
    cdr_completed: bool = False

    # LETTER
    letter_percentage: Optional[int] = 10
    letter_step: Optional[str] = None
    letter_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    letter_error: Optional[str] = None
    letter_completed: bool = False

    

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    Project_Id : str
    Standard: str
    Client_Name: str
    Product: str
    Source_Doc: List[str] = Field(default_factory=list)
    Project_Progress: Optional[ProjectProgress] = None
    Proj_Archived: bool = False
    Proj_Created_On: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    Proj_Created_By: Optional[str] = "system"
    User_Name: Optional[str] = None
    Proj_Deleted_On: Optional[str] = None
    Proj_Deleted_By: Optional[str] = None
    Proj_Archived_On: Optional[str] = None
    Proj_Archived_By: Optional[str] = None


class ProjectFilter(BaseModel):
    user_role: int
    user_email: str | None = None


class FinalizeReportPayload(BaseModel):
    projectId: str
    reportType: str  # "TRF" or "CDR"
    data: dict       # FULL FINAL JSON
