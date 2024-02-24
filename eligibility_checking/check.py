from dataclasses import dataclass, field
import json

from fitz import Document

from .config import StudentType, ELIGIBILITY, Eligibility


@dataclass
class Grades:

    """
    container class for grades
    corresponds to "Transcript Totals" grid at the end of a transcript
    """

    student_type: StudentType = StudentType.UNDETERMINED
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

        # raise an error if the student type (undergraduate/graduate) hasn't been determined
        if self.student_type == StudentType.UNDETERMINED:
            raise AttributeError('student type not yet determined')

        # grab eligibility dictionary for the given student type
        # stores information about cutoffs
        eligibility_dictionary = ELIGIBILITY[self.student_type]

        # find the first valid range
        for key, val in eligibility_dictionary.items():
            lo, hi = key
            if lo <= self.gpa < hi:
                return val

        # return an error if above loop is never finished
        raise ValueError('input not bound between any keys in dictionary')


def get_academic_eligibility(doc: Document) -> Eligibility:

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

    # grab the last non-empty page
    last_page = non_empty_pages[-1]

    # initialize a Grades instance to store grade info in
    totals = Grades()

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
                student_type_str = text_snippets[i+1].strip('()').upper()
                totals.student_type = getattr(StudentType, student_type_str)
                continue

            # continue if text isn't total count
            if txt not in ['Total Institution', 'Total Transfer', 'Overall']:
                continue

            # store next six numbers in the corresponding array in the Grades instance
            attr = txt.lower().replace(' ', '_')
            getattr(totals, attr).extend(float(t) for t in text_snippets[i+1:i+7])
            break

    return totals.eligibility
