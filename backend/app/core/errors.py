"""Maps orchestrator exceptions to HTTP responses (docs/BLUEPRINT.md §6).

Registered once in app.main so every route can just let these exceptions
propagate instead of each one hand-rolling try/except HTTPException.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.auth_errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.rate_limit import RateLimitExceeded
from app.orchestrator.state_machine import (
    InvalidTransitionError,
    OrchestratorError,
    QuestionMismatchError,
    SessionNotFoundError,
)


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error_code": error_code, "message": message}
    )


async def _session_not_found_handler(_request: Request, exc: SessionNotFoundError) -> JSONResponse:
    return _error_response(404, "session_not_found", str(exc))


async def _invalid_transition_handler(
    _request: Request, exc: InvalidTransitionError
) -> JSONResponse:
    return _error_response(409, "invalid_transition", str(exc))


async def _question_mismatch_handler(_request: Request, exc: QuestionMismatchError) -> JSONResponse:
    return _error_response(400, "question_mismatch", str(exc))


async def _orchestrator_error_handler(_request: Request, exc: OrchestratorError) -> JSONResponse:
    return _error_response(500, "orchestrator_error", str(exc))


async def _rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _error_response(429, "rate_limited", str(exc))


async def _email_already_registered_handler(
    _request: Request, exc: EmailAlreadyRegisteredError
) -> JSONResponse:
    return _error_response(409, "email_already_registered", str(exc))


async def _invalid_credentials_handler(
    _request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return _error_response(401, "invalid_credentials", str(exc))


def register_exception_handlers(app: FastAPI) -> None:
    # Registered most-specific first; Starlette dispatches on the exception's
    # exact type against this table, so order here doesn't actually matter,
    # but reads more clearly this way.
    app.add_exception_handler(SessionNotFoundError, _session_not_found_handler)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition_handler)
    app.add_exception_handler(QuestionMismatchError, _question_mismatch_handler)
    app.add_exception_handler(OrchestratorError, _orchestrator_error_handler)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_exception_handler(EmailAlreadyRegisteredError, _email_already_registered_handler)
    app.add_exception_handler(InvalidCredentialsError, _invalid_credentials_handler)
