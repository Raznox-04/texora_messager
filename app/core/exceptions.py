from fastapi import HTTPException, status


class TexoraException(HTTPException):
    """کلاس پایه برای تمام خطاهای سفارشی تکسورا"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(TexoraException):
    """منبع مورد نظر پیدا نشد (404)"""
    def __init__(self, detail: str = "منبع مورد نظر یافت نشد"):
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ForbiddenError(TexoraException):
    """دسترسی مجاز نیست (403)"""
    def __init__(self, detail: str = "دسترسی مجاز نیست"):
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class UnauthorizedError(TexoraException):
    """احراز هویت لازم است (401)"""
    def __init__(self, detail: str = "احراز هویت لازم است"):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class ConflictError(TexoraException):
    """تضاد در داده‌ها (409) - مثلاً نام کاربری تکراری"""
    def __init__(self, detail: str = "تضاد در داده‌ها"):
        super().__init__(detail, status.HTTP_409_CONFLICT)


class ValidationError(TexoraException):
    """داده ورودی نامعتبر است (422)"""
    def __init__(self, detail: str = "داده ورودی نامعتبر است"):
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)