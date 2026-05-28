from threading import Lock

class TokenTracker:
    def __init__(self):
        self.lock = Lock()
        self.reset()

    def reset(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_llm_calls = 0

    def update(
        self,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
    ):
        with self.lock:
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.total_llm_calls += 1

    def to_dict(self):
        return {
            "total_llm_calls": self.total_llm_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }


# Global singleton tracker
token_tracker = TokenTracker()