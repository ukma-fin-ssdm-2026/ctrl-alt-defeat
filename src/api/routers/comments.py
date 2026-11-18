import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.db.database import SessionLocal
from src.api.schemas.comment import CommentCreate, CommentResponse, CommentThreadResponse
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.routers.auth import ensure_within_limit, token_from_request, user_from_token
from src.api.services.bans import ensure_can_contribute
from src.api.services.rate_limit import comment_hour_limiter, comment_minute_limiter
from src.api.utils import check_comment_policy_violations

logger = logging.getLogger(__name__)

# Depth of the deepest allowed reply: 0 = top-level comment, so 5 levels in total
MAX_COMMENT_DEPTH = 4

# Review id travels as a query parameter / body field, so client request URLs stay constant
router = APIRouter(prefix="/api/v1/comments", tags=["comments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_review_or_404(db: Session, review_id) -> models.Review:
    review = db.query(models.Review).filter(models.Review.review_id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})
    return review


@router.get(
    "",
    response_model=CommentThreadResponse,
    summary="Get comments under a review (threaded)",
    responses=STANDARD_ERRORS,
)
def get_comments(
    review_id: UUID4 = Query(..., description="ID of the review"),
    db: Session = Depends(get_db),
):
    _get_review_or_404(db, review_id)
    comments = (
        db.query(models.Comment)
        .filter(models.Comment.review_id == review_id)
        .order_by(models.Comment.created_at.asc(), models.Comment.comment_id.asc())
        .all()
    )

    nodes: Dict = {comment.comment_id: CommentResponse.model_validate(comment) for comment in comments}
    roots: List[CommentResponse] = []
    for comment in comments:
        node = nodes[comment.comment_id]
        parent = nodes.get(comment.parent_id) if comment.parent_id else None
        if parent is not None:
            parent.replies.append(node)
        else:
            roots.append(node)

    return CommentThreadResponse(items=roots, total=len(comments))


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a review or reply to a comment",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "User is not authenticated"},
        403: {"model": ErrorResponse, "description": "The account is banned (FR-009)"},
        409: {"model": ErrorResponse, "description": "The same text as the author's previous comment here"},
        429: {"model": ErrorResponse, "description": "Too many comments from this user; see Retry-After"},
    },
)
def create_comment(
    comment: CommentCreate,
    authorization: Optional[str] = Header(None),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    review_id = comment.review_id

    # Resolve user from JWT access token (FR-001, findings 1 and 17): the same checks as every other
    # endpoint (signature, expiry, existing user, token not revoked by a password change)
    token = token_from_request(authorization, access_token_cookie)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Please log in to leave a comment"},
        )
    try:
        auth_user = user_from_token(db, token)
    except HTTPException as error:
        # Reliability (finding 17): a broken or forged token is worth a line in the log
        if isinstance(error.detail, dict) and error.detail.get("code") == "INVALID_TOKEN":
            logger.warning("Invalid access token provided for comment")
        raise
    user_id = auth_user.user_id
    author_name = auth_user.nickname or "Viewer"

    # FR-009: a banned user cannot comment (team decision: comments are treated like reviews)
    ensure_can_contribute(db, auth_user)

    # Spam protection: a few comments a minute and a limited number an hour per user
    author_key = str(user_id)
    ensure_within_limit(comment_minute_limiter, author_key, "Too many comments in a short time.")
    ensure_within_limit(comment_hour_limiter, author_key, "Too many comments in the last hour.")

    _get_review_or_404(db, review_id)

    violations = check_comment_policy_violations(comment.text)
    if violations:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "POLICY_VIOLATION",
                "message": f"Comment contains forbidden content: {', '.join(violations)}",
            },
        )

    depth = 0
    if comment.parent_id is not None:
        parent = db.query(models.Comment).filter(models.Comment.comment_id == comment.parent_id).first()
        if parent is None or parent.review_id != review_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "PARENT_COMMENT_NOT_FOUND", "message": "Parent comment not found under this review"},
            )
        depth = parent.depth + 1
        if depth > MAX_COMMENT_DEPTH:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "MAX_DEPTH_EXCEEDED",
                    "message": f"Replies can be nested at most {MAX_COMMENT_DEPTH + 1} levels deep",
                },
            )

    # The same text twice in a row under one review is a double click or spam
    last_comment = (
        db.query(models.Comment)
        .filter(models.Comment.review_id == review_id, models.Comment.user_id == user_id)
        .order_by(models.Comment.created_at.desc())
        .first()
    )
    if last_comment is not None and last_comment.text.strip().casefold() == comment.text.casefold():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_COMMENT", "message": "You have already posted this comment under the review"},
        )

    db_comment = models.Comment(
        review_id=review_id,
        parent_id=comment.parent_id,
        user_id=user_id,
        author_name=author_name,
        text=comment.text,
        depth=depth,
        # Set explicitly: microsecond precision keeps the thread order stable
        created_at=datetime.now(UTC),
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    comment_minute_limiter.record(author_key)
    comment_hour_limiter.record(author_key)
    return db_comment
