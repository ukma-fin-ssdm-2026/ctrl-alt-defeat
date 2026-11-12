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
    # Every access token issued before this moment stops working (other devices are logged out)
    user.token_version = (user.token_version or 0) + 1
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
    remove_user_with_data(db, user)


def admin_delete_user(db: Session, admin: models.User, user_id) -> None:
    """An administrator removes a user (e.g. a spam account) without the user's password."""
    target = db.query(models.User).filter(models.User.user_id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    if target.user_id == admin.user_id:
        raise HTTPException(
            status_code=400, detail={"code": "CANNOT_DELETE_SELF", "message": "You cannot delete your own account here"}
        )
    if target.role == "admin":
        raise HTTPException(
            status_code=400, detail={"code": "CANNOT_DELETE_ADMIN", "message": "Administrators cannot be deleted"}
        )
    if is_seed_account(target.email):
        raise HTTPException(status_code=400, detail=SEED_ACCOUNT)
    remove_user_with_data(db, target)


def remove_user_with_data(db: Session, user: models.User) -> None:
    """Delete the user with reviews, votes, ratings, comments (also replies under their reviews), lists and bans."""
    user_id = user.user_id
    review_ids = [row.review_id for row in db.query(models.Review.review_id).filter(models.Review.user_id == user_id)]
    # Explicit deletes: SQLite does not enforce ON DELETE CASCADE without a pragma
    comments = db.query(models.Comment).filter(models.Comment.user_id == user_id)
    if review_ids:
        comments = db.query(models.Comment).filter(
            (models.Comment.user_id == user_id) | (models.Comment.review_id.in_(review_ids))
        )
    comments.delete(synchronize_session=False)
    # Votes of the user and votes under the user's reviews
    votes = db.query(models.ReviewVote).filter(models.ReviewVote.user_id == user_id)
    if review_ids:
        votes = db.query(models.ReviewVote).filter(
            (models.ReviewVote.user_id == user_id) | (models.ReviewVote.review_id.in_(review_ids))
        )
    votes.delete(synchronize_session=False)
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
