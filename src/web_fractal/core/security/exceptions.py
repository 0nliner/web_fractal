class AccessDenied(Exception):
    pass


class FieldNotVisible(AccessDenied):
    pass


class OperationNotAllowed(AccessDenied):
    pass
