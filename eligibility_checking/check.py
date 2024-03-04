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
    """
    container class for grades
    corresponds to "Transcript Totals" grid at the end of a transcript
    """

    student_type: StudentType = field(init=False)
    full_name: str = field(init=False)
    gpa: float = field(init=False)

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

    def validate(self, attr_to_check: str, correct_type: type) -> None:
        """
        validate that a particular attr is the correct type, throw an error if not
        """

        try:
            attr = getattr(self, attr_to_check)
            attr_check = isinstance(attr, correct_type)
            assert attr_check
        except AttributeError as e:
            raise ValueError(f"{attr_to_check} is not correctly stored") from e

        if not attr_check:
            raise ValueError(f"{attr_to_check} is not type {correct_type}")

    def validate_all(self) -> None:
        """
        validate all attrs in class
        """

        self.validate("student_type", StudentType)
        self.validate("full_name", str)
        self.validate("gpa", float)


def contains_text(document: HotPdf, text: str) -> bool:

    found_text = document.find_text(text)
    for hot_character in found_text.values():
        if len(hot_character) != 0:
            return True

    return False


def get_grades(doc: HotPdf, page_width: int = 1_000_000) -> Grades:

    grades = Grades()

    num_pages = len(doc.pages)

    occurrences = doc.find_text("Overall", take_span=True)
    gpa = None
    for page in range(num_pages):
        try:
            dims = occurrences[page][-1]
            element_dim = get_element_dimension(dims)
            span = doc.extract_text(x0=element_dim.x0, y0=element_dim.y0, x1=page_width, y1=element_dim.y1, page=page)
            gpa = span.strip()[-4:]
            break
        except IndexError:
            pass
    if gpa is None:
        raise ValueError("GPA occurrence not found")
    grades.gpa = float(gpa)

    if contains_text(doc, "Undergraduate"):
        occurrences = doc.find_text("Undergraduate", take_span=True)
        grades.student_type = StudentType.UNDERGRADUATE
    elif contains_text(doc, "Graduate"):
        occurrences = doc.find_text("Graduate", take_span=True)
        grades.student_type = StudentType.GRADUATE
    else:
        raise ValueError("student type text instance not found")

    element_dim = get_element_dimension(occurrences[0][1])
    span = doc.extract_text(x0=0, y0=element_dim.y0, x1=page_width, y1=element_dim.y1, page=0)
    matches = re.match(r"(.+)(\d{2}/\d{2}/\d{4})(.+)", span)
    grades.full_name = matches.group(1)

    return grades
