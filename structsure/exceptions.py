class MaxRetriesExceededError(Exception):
    """
    Raised when the LLM fails to produce a valid JSON output that matches the Pydantic schema
    after the maximum number of retries.
    """

    def __init__(self, message="LLM failed to produce valid JSON after multiple retries."):
        self.message = message
        super().__init__(self.message)
