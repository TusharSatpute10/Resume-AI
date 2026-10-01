from enum import Enum


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    HR = "HR"
    ADMIN = "ADMIN"