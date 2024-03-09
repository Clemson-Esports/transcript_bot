"""
Module for computing necessary data from a submitted transcript
"""

from dataclasses import dataclass, field
from enum import Enum
import re

import yaml
from hotpdf import HotPdf
from hotpdf.utils import get_element_dimension

# need to parse input config
# code is called from parent directory
# so config file needs to be referenced as if we are in parent directory

with open("config.yaml", "r") as file:
    CONFIG_DATA = yaml.safe_load(file)

StudentType = Enum("StudentType", CONFIG_DATA["StudentType"])
Eligibility = Enum("Eligibility", CONFIG_DATA["Eligibility"])

ELIGIBILITY = dict()
for student_type_str, ranges in CONFIG_DATA["ELIGIBILITY"].items():
    reformatted_ranges = dict()
    for r in ranges:
        reformatted_ranges[tuple(r["range"])] = getattr(Eligibility, r["eligibility"])
    ELIGIBILITY[getattr(StudentType, student_type_str)] = reformatted_ranges


@dataclass
class Grades:

    student_type: StudentType
    full_name: str
    gpa: float

    @property
    def eligibility(self) -> Eligibility:
        """
        get eligibility from totals data
        """

        # grab eligibility dictionary for the given student type
        # stores information about cutoffs
        try:
            eligibility_dictionary = ELIGIBILITY[self.student_type]
        except AttributeError as e:
            raise ValueError("student type not yet initialized") from e

        # find the first valid range
        for key, val in eligibility_dictionary.items():
            lo, hi = key
            if lo <= self.gpa < hi:
                return val

        # return an error if above loop is never finished
        raise ValueError("input not bound between any keys in dictionary")


def get_grades(doc: HotPdf) -> Grades:

    text = "".join(doc.extract_page_text(page=p) for p in range(len(doc.pages)))

    (fullname_birthday_status,) = re.finditer(
        r"(.+)\d{2}/\d{2}/\d{4}Continuing (Graduate|Undergraduate)", text
    )
    full_name = fullname_birthday_status.group(1)
    status = fullname_birthday_status.group(2)

    (overall,) = re.finditer(
        r"Overall\d{1,3}.000\d{1,3}.000\d{1,3}.000\d{1,3}.00\d{1,3}.00(\d.\d\d)", text
    )
    gpa = overall.group(1)

    return Grades(
        student_type=getattr(StudentType, status.upper()),
        full_name=full_name,
        gpa=float(gpa),
    )
