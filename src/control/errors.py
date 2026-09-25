"""Execution boundary signals understood by the control chain."""


class ReviewRequired(PermissionError):
    pass


class PolicyDenied(PermissionError):
    pass
