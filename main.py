import sys

import fitz

from eligibility_checking.check import get_academic_eligibility


def main():

    doc = fitz.open(sys.argv[1])
    eligibility = get_academic_eligibility(doc)
    print(eligibility)


if __name__ == '__main__':

    main()
