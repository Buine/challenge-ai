from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class IssueType(StrEnum):
    ORPHANED_PAYMENT = "ORPHANED_PAYMENT"
    STUCK_PENDING = "STUCK_PENDING"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    ZOMBIE_COMPLETION = "ZOMBIE_COMPLETION"
    POST_EXPIRATION_PAYMENT = "POST_EXPIRATION_PAYMENT"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PaymentMethod(StrEnum):
    OXXO = "OXXO"
    EFECTY = "EFECTY"


class Currency(StrEnum):
    MXN = "MXN"
    COP = "COP"
