from apps.execution.services import ExecutionService


def execution_status(request):
    if not request.user.is_authenticated:
        return {"execution_status": None}

    payload = ExecutionService.build_session_payload(request.user)
    return {"execution_status": payload}
