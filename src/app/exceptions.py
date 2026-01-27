from src.app.messages import USER_WITH_EMAIL_EXIST_ERROR


class UserAlreadyExistsException(Exception):
    def __init__(self, email: str):
        self.email = email
        super().__init__(USER_WITH_EMAIL_EXIST_ERROR.format(email=self.email))
