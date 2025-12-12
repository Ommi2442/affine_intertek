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
    Client_Name: str
    Product: str



class ProjectProgress(BaseModel):
    # TRF
    trf_percentage: Optional[int] = 33
    trf_step: Optional[str] = None
    trf_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    trf_error: Optional[str] = None
    trf_completed: Optional[str] = 'No'

    # CDR
    cdr_percentage: Optional[int] = 33
    cdr_step: Optional[str] = None
    cdr_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    cdr_error: Optional[str] = None
    cdr_completed: Optional[str] = 'No'

    # LETTER
    letter_percentage: Optional[int] = 33
    letter_step: Optional[str] = None
    letter_last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    letter_error: Optional[str] = None
    letter_completed: Optional[str] = 'No'

    

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    Project_Id : str
    Standard: str
    Client_Name: str
    Product: str
    Source_Doc: List[str] = Field(default_factory=list)
    Project_Progress: Optional[ProjectProgress] = None
    TRF_Generated: bool = False
    TRF_Data: List[TRFItem] = Field(default_factory=list)
    TRF_Generated_On: Optional[str] = None
    TRF_Generated_By: Optional[str] = None
    TRF_Reviewed_On: Optional[str] = None
    TRF_Reviewed_By: Optional[str] = None
    TRF_Approved_On: Optional[str] = None
    TRF_Approved_By: Optional[str] = None
    TRF_Status: Optional[str] = None
    TRF_Regenerated_On: Optional[str] = None
    TRF_Regenerated_By: Optional[str] = None
    CDR_Generated: bool = False
    CDR_Data: List[CDRItem] = Field(default_factory=list)
    CDR_Generated_On: Optional[str] = None
    CDR_Generated_By: Optional[str] = None
    CDR_Reviewed_On: Optional[str] = None
    CDR_Reviewed_By: Optional[str] = None
    CDR_Approved_On: Optional[str] = None
    CDR_Approved_By: Optional[str] = None
    CDR_Status: Optional[str] = None
    CDR_Regenerated_On: Optional[str] = None
    CDR_Regenerated_By: Optional[str] = None
    Letter_Generated: bool = False
    Letter_Data: List[LetterItem] = Field(default_factory=list)
    Letter_Generated_On: Optional[str] = None
    Letter_Generated_By: Optional[str] = None
    Letter_Reviewed_On: Optional[str] = None
    Letter_Reviewed_By: Optional[str] = None
    Letter_Approved_On: Optional[str] = None
    Letter_Approved_By: Optional[str] = None
    Letter_Status: Optional[str] = None
    Letter_Regenerated_On: Optional[str] = None
    Letter_Regenerated_By: Optional[str] = None
    Proj_Created_On: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    Proj_Created_By: Optional[str] = "system"
    Proj_Deleted_On: Optional[str] = None
    Proj_Deleted_By: Optional[str] = None
    Proj_Archived_On: Optional[str] = None
    Proj_Archived_By: Optional[str] = None


class ProjectFilter(BaseModel):
    user_role: int
    user_email: str | None = None


