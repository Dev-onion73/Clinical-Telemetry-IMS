from datetime import date
from enum import Enum

from pydantic import BaseModel


class Sex(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class BloodGroup(str, Enum):
    A_POSITIVE = "A_POSITIVE"
    A_NEGATIVE = "A_NEGATIVE"
    B_POSITIVE = "B_POSITIVE"
    B_NEGATIVE = "B_NEGATIVE"
    AB_POSITIVE = "AB_POSITIVE"
    AB_NEGATIVE = "AB_NEGATIVE"
    O_POSITIVE = "O_POSITIVE"
    O_NEGATIVE = "O_NEGATIVE"
    UNKNOWN = "UNKNOWN"


class PatientCreate(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex = Sex.UNKNOWN
    blood_group: BloodGroup = BloodGroup.UNKNOWN


class PatientResponse(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    blood_group: BloodGroup