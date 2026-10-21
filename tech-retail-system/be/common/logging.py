import logging
import re


class RedactOAuthQuery(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(
            r"(/api/v1/auth/(?:google|facebook)/callback/)\?[^\s\"']+",
            r"\1?[redacted]",
            record.getMessage(),
        )
        record.msg = re.sub(
            r"(/api/v1/payments/vnpay/(?:ipn|return)/)\?[^\s\"']+", r"\1?[redacted]", record.msg
        )
        record.args = ()
        return True
