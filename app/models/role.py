import enum


class RoleEnum(str, enum.Enum):
    student = "student"
    company = "company"
    program_manager = "program_manager"
    admin = "admin"
