import base64
import re
import binascii

km_pattern = re.compile(r'^01\d{14}21\d{1}[A-Za-z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/\\|`~\-]{6}\x1d93[A-Za-z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/\\|`~\-]{4}$')
ka_pattern = re.compile(r'^02\d{14}\x1d37\d{2}\x1d21[A-Za-z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/\\|`~\-]+$')


def code_validator(code_pattern):
    def validator(input_code: str, pattern):
        try:
            decoded_code = base64.b64decode(input_code).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            return False
        return bool(pattern.match(decoded_code))
    return lambda input_code: validator(input_code, code_pattern)

is_km_valid = code_validator(km_pattern)
is_ka_valid = code_validator(ka_pattern)

# # Пример использования
# kms = ["MDEwNDY4MDU3MTA2MTIyNjIxNVlGWC8wbh05M1VlVSs=",
#                  "MDEwNDY4MDU3MTA2MTIyNjIxNUVpZzUmbx05M3cxbS8=",
#                  "MDEwNDY4MDU3MTA2MTIyNjIxNT5QaFZzKB05MzlMRng=",
#                  "MDEwNDY4MDU3MTA2MTIyNjIxNUpDVCxyTR05M3IremU=",
#                  "MDEwNDY4MDU3MTA2MTIyNjIxNS9LO2hZMB05M2VQd0g="]
#
# for code in kms:
#     print(base64.b64decode(code).decode("utf-8"), marking_code_validator(code))  # True или False
#
# kas = ["MDIwNDY4MDU3MTA2MTIyNh0zNzEyHTIxQUEwMzM=",]
#
# for code in kas:
#     print(base64.b64decode(code).decode("utf-8"), aggregate_code_validator(code))  # True или False