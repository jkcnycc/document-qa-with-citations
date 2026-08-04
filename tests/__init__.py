import logging

# The refusal paths log warnings by design; silence them so test output stays
# readable. Behaviour is asserted on the returned Answer, not on log lines.
logging.disable(logging.WARNING)
