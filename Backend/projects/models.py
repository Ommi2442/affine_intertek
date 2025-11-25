from pydantic import BaseModel
from typing import List, Optional


class TRFItem(BaseModel):
    TRF_No: str
    TRF_Date: str


class CDRItem(BaseModel):
    CDR_No: str
    CDR_Date: str


class LetterItem(BaseModel):
    Letter_No: str
    Letter_Date: str



class Project(BaseModel):
    id: Optional[str] = None
    Project_Id: str =""
    Proj_Name: str
    Standard: str
    Client_Name: str
    Product: str
    Source_Doc: List[str] = []
    TRF_Generated: str = False
    TRF_Data: List[TRFItem] = []
    TRF_Generated_On: str = None
    TRF_Generated_By: str = None
    TRF_Reviewed_On: str = None
    TRF_Reviewed_By: str = None
    TRF_Approved_On: str = None
    TRF_Approved_By: str = None
    TRF_Status: str = None
    TRF_Regenerated_On: str = None
    TRF_Regenerated_By: str = None

    CDR_Generated: str = False
    CDR_Data: List[CDRItem] = []
    CDR_Generated_On: str = None
    CDR_Generated_By: str = None
    CDR_Reviewed_On: str = None
    CDR_Reviewed_By: str = None
    CDR_Approved_On: str = None
    CDR_Approved_By: str = None
    CDR_Status: str = None
    CDR_Regenerated_On: str = None
    CDR_Regenerated_By: str = None

    Letter_Generated: str = False
    Letter_Data: List[LetterItem] = []
    Letter_Generated_On: str = None
    Letter_Generated_By: str = None
    Letter_Reviewed_On: str = None
    Letter_Reviewed_By: str = None
    Letter_Approved_On: str = None
    Letter_Approved_By: str = None
    Letter_Status: str = None
    Letter_Regenerated_On: str = None
    Letter_Regenerated_By: str = None

    Proj_Created_On: str
    Proj_Created_By: str
    Proj_Deleted_On: str = None
    Proj_Deleted_By: str = None
    Proj_Archived_On: str = None
    Proj_Archived_By: str = None
