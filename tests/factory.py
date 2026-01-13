from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from fastapi_users.password import PasswordHelper
from src.app.models.db_models import CatalogItem, Product, User

from factory import LazyFunction, Sequence  # type: ignore[attr-defined]

PASSWORD = "password"
hashed_password = PasswordHelper().hash(PASSWORD)

fake = Faker()


def get_password_hash(password: str) -> str:
    return PasswordHelper().hash(password)


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    email = LazyFunction(lambda: fake.email())  # type: ignore
    hashed_password = LazyFunction(lambda: get_password_hash(PASSWORD))  # type: ignore


class CatalogItemFactory(SQLAlchemyModelFactory):
    class Meta:
        model = CatalogItem
        sqlalchemy_session_persistence = "flush"

    name = LazyFunction(lambda: fake.word())  # type: ignore
    description = LazyFunction(lambda: fake.text(max_nb_chars=200))  # type: ignore


class ProductFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Product
        sqlalchemy_session_persistence = "flush"

    catalog_item_id = Sequence(lambda n: n + 1)  # type: ignore
    sell_price = LazyFunction(
        lambda: round(
            fake.pyfloat(positive=True, min_value=10, max_value=1000), 2
        )  # type: ignore
    )
    purchase_price = LazyFunction(
        lambda: round(
            fake.pyfloat(positive=True, min_value=5, max_value=800), 2
        )  # type: ignore
    )
