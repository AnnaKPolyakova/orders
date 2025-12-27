from faker import Faker
from fastapi_users.password import PasswordHelper
from src.app.models.db_models import User

import factory

PASSWORD = "password"
hashed_password = PasswordHelper().hash(PASSWORD)

fake = Faker()


def get_password_hash(password: str) -> str:
    return PasswordHelper().hash(password)


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    email = factory.LazyFunction(lambda: fake.email())  # type: ignore
    hashed_password = factory.LazyFunction(lambda: get_password_hash(PASSWORD))  # type: ignore
