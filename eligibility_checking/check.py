from dataclasses import dataclass, field
import json
from enum import Enum

from fitz import Document
import yaml

with open('config.yaml', 'r') as file:
    CONFIG_DATA = yaml.safe_load(file)

# load student types as Enum

StudentType = Enum('StudentType', CONFIG_DATA["StudentType"])
Eligibility = Enum('Eligibility', CONFIG_DATA["Eligibility"])

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
    total_institution: list[float] = field(default_factory=list)
    total_transfer: list[float] = field(default_factory=list)
    overall: list[float] = field(default_factory=list)

    @property
    def gpa(self) -> float:

        """
        get gpa from overall list
        """

        # raise error if overall list isn't stored yet
        if not self.overall:
            raise AttributeError('gpa not yet stored from document')

        return self.overall[-1]

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
        raise ValueError('input not bound between any keys in dictionary')


def get_grades(doc: Document) -> Grades:

    """
    get eligibility from fitz document
    """

    # load pages as json format
    json_doc = [
        json.loads(page.get_text('json')) for page in doc
    ]

    # grab the non-empty pages in the document
    non_empty_pages = [
        page for page in json_doc if page['blocks']
    ]

    # initialize a Grades instance to store grade info in
    totals = Grades()

    # grab first page with student info
    first_page = non_empty_pages[0]

    name_line = None
    for i, block in enumerate(first_page['blocks']):
        lines = block['lines']
        if len(lines) != 1:
            continue
        line = lines[0]
        spans = line['spans']
        if len(spans) != 1:
            continue
        txt = spans[0]['text']
        if txt == 'Name':
            name_line = i + 1
            break

    if not name_line:
        raise ValueError

    totals.full_name = first_page['blocks'][name_line]['lines'][0]['spans'][0]['text']

    # grab the last non-empty page
    last_page = non_empty_pages[-1]

    # loop through blocks in the last page
    for block in last_page['blocks']:

        # grab text snippets from blocks with single lines
        lines = block['lines']
        single_text_lines = [
            line for line in lines if len(line['spans']) == 1
        ]
        text_snippets = [
            line['spans'][0]['text'] for line in single_text_lines
        ]

        # loop through text snippets
        for i, txt in enumerate(text_snippets):
            if txt == 'Transcript Totals -':
                # grab the student type from the snippet after Transcript Totals
                # store in Grades instance
                totals.student_type = getattr(
                    StudentType,
                    text_snippets[i+1].strip('()').upper()
                )
                continue

            # continue if text isn't total count
            if txt not in ['Total Institution', 'Total Transfer', 'Overall']:
                continue

            # store next six numbers in the corresponding array in the Grades instance
            attr = txt.lower().replace(' ', '_')
            getattr(totals, attr).extend(float(t) for t in text_snippets[i+1:i+7])
            break

    return totals
