# from pydantic import BaseModel
# from typing import List, Optional


# # ---------------------------
# # Sub-Models
# # ---------------------------

# class TRFItem(BaseModel):
#     TRF_No: str
#     TRF_Date: str


# class CDRItem(BaseModel):
#     CDR_No: str
#     CDR_Date: str


# class LetterItem(BaseModel):
#     Letter_No: str
#     Letter_Date: str


# # ---------------------------
# # Model: User INPUT (Frontend)
# # ---------------------------

# class ProjectCreate(BaseModel):
#     Standard: str
#     Client_Name: str
#     Product: str

# class Project(BaseModel):
#     id: Optional[str] = None                 
#     Project_Id: str = ""                     
#     Proj_Name: str = ""

#     # User Provided
#     Standard: str
#     Client_Name: str
#     Product: str

#     # Auto / Default Fields
#     Source_Doc: List[str] = []

#     # TRF Section
#     TRF_Generated: str = False
#     TRF_Data: List[TRFItem] = []
#     TRF_Generated_On: str = None
#     TRF_Generated_By: str = None
#     TRF_Reviewed_On: str = None
#     TRF_Reviewed_By: str = None
#     TRF_Approved_On: str = None
#     TRF_Approved_By: str = None
#     TRF_Status: str = None
#     TRF_Regenerated_On: str = None
#     TRF_Regenerated_By: str = None

#     # CDR Section
#     CDR_Generated: str = False
#     CDR_Data: List[CDRItem] = []
#     CDR_Generated_On: str = None
#     CDR_Generated_By: str = None
#     CDR_Reviewed_On: str = None
#     CDR_Reviewed_By: str = None
#     CDR_Approved_On: str = None
#     CDR_Approved_By: str = None
#     CDR_Status: str = None
#     CDR_Regenerated_On: str = None
#     CDR_Regenerated_By: str = None

#     # Letter Section
#     Letter_Generated: str = False
#     Letter_Data: List[LetterItem] = []
#     Letter_Generated_On: str = None
#     Letter_Generated_By: str = None
#     Letter_Reviewed_On: str = None
#     Letter_Reviewed_By: str = None
#     Letter_Approved_On: str = None
#     Letter_Approved_By: str = None
#     Letter_Status: str = None
#     Letter_Regenerated_On: str = None
#     Letter_Regenerated_By: str = None
#     Proj_Created_On: str = "string"
#     Proj_Created_By: str = "string"
#     Proj_Deleted_On: str = None
#     Proj_Deleted_By: str = None
#     Proj_Archived_On: str = None
#     Proj_Archived_By: str = None

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


# ---------------------------
# Sub-Models
# ---------------------------

class TRFItem(BaseModel):
    TRF_No: str
    TRF_Date: str


class CDRItem(BaseModel):
    CDR_No: str
    CDR_Date: str


class LetterItem(BaseModel):
    Letter_No: str
    Letter_Date: str


# ---------------------------
# Model: User INPUT (Frontend)
# ---------------------------

class ProjectCreate(BaseModel):
    Standard: str
    Client_Name: str
    Product: str


# ---------------------------
# Model: STORED IN COSMOS DB
# ---------------------------

class Project(BaseModel):
    # Auto fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    Project_Id: str = ""
    Proj_Name: Optional[str] = None

    # User provided
    Standard: str
    Client_Name: str
    Product: str

    # Auto fields
    Source_Doc: List[str] = Field(default_factory=list)

    # TRF Section
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

    # CDR Section
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

    # Letter Section
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

    # Project Metadata
    Proj_Created_On: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    Proj_Created_By: Optional[str] = "system"
    Proj_Deleted_On: Optional[str] = None
    Proj_Deleted_By: Optional[str] = None
    Proj_Archived_On: Optional[str] = None
    Proj_Archived_By: Optional[str] = None
