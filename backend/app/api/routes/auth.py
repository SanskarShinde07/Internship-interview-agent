"""Auth routes (docs/BLUEPRINT.md §21 follow-up): register, login, current
user, password reset, and a signed-in candidate's own interview history.

Deliberately thin: no separate service/orchestrator layer the way the
interview flow has one, because there's no state machine here - each
route is a couple of DB lookups plus a call into app.core.security. Kept
that way rather than adding a layer that would just forward arguments.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SessionHistoryItem,
    SessionHistoryResponse,
    UserResponse,
)
from app.config import get_settings
from app.core.auth_errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.email import send_password_reset_email
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import Candidate, InterviewReport, InterviewSession, User

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> AuthResponse:
    email = payload.email.lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> AuthResponse:
    email = payload.email.lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password.")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> ForgotPasswordResponse:
    # Always the same response whether or not the email is registered -
    # otherwise this endpoint becomes a way to enumerate registered emails.
    generic_message = "If that email is registered, a reset link has been sent."

    email = payload.email.lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is not None:
        settings = get_settings()
        token = create_reset_token(user.id)
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        send_password_reset_email(user.email, reset_link)

    return ForgotPasswordResponse(message=generic_message)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> ResetPasswordResponse:
    try:
        user_id = decode_token(payload.token, expected_purpose="reset")
    except InvalidTokenError as exc:
        raise InvalidCredentialsError(str(exc)) from exc

    user = db.get(User, user_id)
    if user is None:
        raise InvalidCredentialsError("This reset link is no longer valid.")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return ResetPasswordResponse(message="Your password has been updated.")


@router.get("/me/interviews", response_model=SessionHistoryResponse)
def get_my_interviews(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SessionHistoryResponse:
    rows = db.execute(
        select(InterviewSession, InterviewReport)
        .join(Candidate, InterviewSession.candidate_id == Candidate.id)
        .outerjoin(InterviewReport, InterviewReport.session_id == InterviewSession.id)
        .where(Candidate.user_id == current_user.id)
        .order_by(InterviewSession.started_at.desc().nullslast())
    ).all()

    items = [
        SessionHistoryItem(
            session_id=session.id,
            state=session.state,
            started_at=session.started_at,
            completed_at=session.completed_at,
            overall_score=report.overall_score if report else None,
            readiness_level=report.readiness_level.value if report else None,
        )
        for session, report in rows
    ]
    return SessionHistoryResponse(sessions=items)
