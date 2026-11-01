from datetime import UTC, datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.db.database import SessionLocal
from src.api.schemas.comment import CommentCreate, CommentResponse, CommentThreadResponse
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.utils import check_comment_policy_violations

# Depth of the deepest allowed reply: 0 = top-level comment, so 5 levels in total
MAX_COMMENT_DEPTH = 4

router = APIRouter(prefix="/api/v1/reviews", tags=["comments"])


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
    "/{review_id}/comments",
    response_model=CommentThreadResponse,
    summary="Get comments under a review (threaded)",
    responses=STANDARD_ERRORS,
)
def get_comments(
    review_id: UUID4 = Path(..., description="ID of the review"),
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
    "/{review_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a review or reply to a comment",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "User is not authenticated"},
    },
)
def create_comment(
    comment: CommentCreate,
    review_id: UUID4 = Path(..., description="ID of the review"),
    db: Session = Depends(get_db),
):
    # TODO(FR-001): take the user from the access token
    if comment.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Please log in to leave a comment"},
        )

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

    db_comment = models.Comment(
        review_id=review_id,
        parent_id=comment.parent_id,
        user_id=comment.user_id,
        author_name=comment.author_name,
        text=comment.text,
        depth=depth,
        # Set explicitly: microsecond precision keeps the thread order stable
        created_at=datetime.now(UTC),
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment
