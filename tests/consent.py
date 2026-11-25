"""Simulate an audible, affirmative answer only to the exact proposed visit."""


def perform(call, name, args, request):
    result = call.invoke(name, args, request)
    if result.get("error") == "CONFIRM_SLOT":
        call.assistant(result["question"])
        call.user("yes")
        return call.invoke(name, args, request)
    return result
