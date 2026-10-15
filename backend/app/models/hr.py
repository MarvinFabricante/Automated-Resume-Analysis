from sqlalchemy import *

from app.models.user import User


class HR(User):
    __tablename__ = "hr_staffs"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    company_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    position = Column(String, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "HR",
    }