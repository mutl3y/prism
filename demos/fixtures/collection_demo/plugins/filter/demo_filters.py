"""Filter plugin fixture for Prism collection demo."""


def upper_trimmed(value):
    return str(value).strip().upper()


class FilterModule:
    def filters(self):
        return {
            "upper_trimmed": upper_trimmed,
        }
