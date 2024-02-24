from enum import Enum


class StudentType(Enum):

    """
    Enum for student types
    """

    UNDETERMINED = -1
    UNDERGRADUATE = 0
    GRADUATE = 1


class Eligibility(Enum):

    """
    Enum for eligibility types
    """

    INELIGIBLE = 0
    PROBATION = 1
    ELIGIBLE = 2


# eligibility ranges, need the small number since comparison is not right-inclusive
EPSILON = 1.0e-2
ELIGIBILITY = {
    StudentType.UNDERGRADUATE: {
        (0.0, 2.0): Eligibility.INELIGIBLE,
        (2.0, 2.5): Eligibility.PROBATION,
        (2.5, 4.0 + EPSILON): Eligibility.ELIGIBLE
    },
    StudentType.GRADUATE: {
        (0.0, 2.5): Eligibility.INELIGIBLE,
        (2.5, 3.0): Eligibility.PROBATION,
        (3.0, 4.0 + EPSILON): Eligibility.ELIGIBLE
    }
}
