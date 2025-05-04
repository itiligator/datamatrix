import random
import string
import base64
from typing import List

COUNTRY_CODE = 5
MIN_SERIAL_NUMBER_LENGTH = 5
MAX_SERIAL_NUMBER_LENGTH = 5


def gtin_from_codes(codes: List[str]) -> str:
    """
    Extracts the GTIN from a list of base64 encoded codes.
    :param codes: List of codes
    :return: GTIN
    """
    if not codes:
        raise ValueError("No codes provided")
    gtins = [(base64.b64decode(code).decode('utf-8'))[2:16] for code in codes]
    # check that all gtins are the same
    if len(gtins) == 0:
        raise ValueError("Something went wrong with GTINS extraction")
    if len(set(gtins)) != 1:
        raise ValueError("Different GTINs found in the codes")
    gtin = gtins[0]
    return gtin


def _generate_ka_code(gtin: str, count: int) -> str:
    serial_number = ''.join(
        random.choices(string.ascii_letters + string.digits,
                       k=random.randint(MIN_SERIAL_NUMBER_LENGTH, MAX_SERIAL_NUMBER_LENGTH)))

    return base64.b64encode(f"02{gtin}\x1d37{count:02}\x1d21{serial_number}".encode('utf-8')).decode(
        'utf-8')


def ka_code(codes: List[str]) -> str:
    gtin = gtin_from_codes(codes)
    return _generate_ka_code(gtin, len(codes))
