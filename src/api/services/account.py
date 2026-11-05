"""Account self-service: change the password and delete the account with all personal data."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.services.auth import hash_password, verify_password
from src.api.services.demo_accounts import is_seed_account

INVALID_PASSWORD = {"code": "INVALID_PASSWORD", "message": "The current password is incorrect"}
SEED_ACCOUNT = {
    "code": "SEED_ACCOUNT_LOCKED",
    "message": "Demo accounts are managed by the server settings and cannot be changed or deleted",
}


def _check_password(user: models.User, password: str) -> None:
    # 400, not 401: the session itself is valid, only the confirmation is wrong
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_PASSWORD)


def change_password(db: Session, user: models.User, current_password: str, new_password: str) -> None:
    if is_seed_account(user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEED_ACCOUNT)
    _check_password(user, current_password)
    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SAME_PASSWORD", "message": "The new password must differ from the current one"},
        )
    user.password_hash = hash_password(new_password)
    db.commit()


def delete_account(db: Session, user: models.User, password: str) -> None:
    """Remove the user and everything they created (reviews, ratings, comments, lists, bans)."""
    if is_seed_account(user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEED_ACCOUNT)
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_ACCOUNT", "message": "Administrator accounts cannot be deleted from the profile"},
        )
    _check_password(user, password)

    user_id = user.user_id
    review_ids = [row.review_id for row in db.query(models.Review.review_id).filter(models.Review.user_id == user_id)]
    # Explicit deletes: SQLite does not enforce ON DELETE CASCADE without a pragma
    comments = db.query(models.Comment).filter(models.Comment.user_id == user_id)
    if review_ids:
        comments = db.query(models.Comment).filter(
            (models.Comment.user_id == user_id) | (models.Comment.review_id.in_(review_ids))
        )
    comments.delete(synchronize_session=False)
    db.query(models.Review).filter(models.Review.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Rating).filter(models.Rating.user_id == user_id).delete(synchronize_session=False)
    db.query(models.WatchedItem).filter(models.WatchedItem.user_id == user_id).delete(synchronize_session=False)
    db.query(models.WatchlistItem).filter(models.WatchlistItem.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Ban).filter(models.Ban.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Ban).filter(models.Ban.admin_id == user_id).update(
        {models.Ban.admin_id: None}, synchronize_session=False
    )
    db.delete(user)
    db.commit()
