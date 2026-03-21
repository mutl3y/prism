"""Demo Jinja test plugin fixture."""


def is_even_length(value):
    return len(str(value)) % 2 == 0


class TestModule:
    def tests(self):
        return {
            "even_length": is_even_length,
        }
