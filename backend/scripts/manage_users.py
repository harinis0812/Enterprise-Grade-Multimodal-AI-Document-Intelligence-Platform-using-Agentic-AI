import argparse
import sys
from backend.database.database import SessionLocal
from backend.database.models import User, AuditLog
from backend.core.security import log_audit_event


def promote_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            print(f"[Error] User with email '{email}' was not found.")
            sys.exit(1)

        user.role = "admin"
        db.commit()

        log_audit_event(
            db=db,
            event_type="ADMIN_CLI_USER_PROMOTED",
            user_id=user.id,
            details=f"User {user.email} promoted to admin via CLI tool."
        )
        print(f"[Success] User '{user.email}' (ID: {user.id}) has been promoted to 'admin'.")
    finally:
        db.close()


def demote_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            print(f"[Error] User with email '{email}' was not found.")
            sys.exit(1)

        user.role = "user"
        db.commit()

        log_audit_event(
            db=db,
            event_type="ADMIN_CLI_USER_DEMOTED",
            user_id=user.id,
            details=f"User {user.email} demoted to user via CLI tool."
        )
        print(f"[Success] User '{user.email}' (ID: {user.id}) has been set to role 'user'.")
    finally:
        db.close()


def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        print(f"\nTotal Registered Users: {len(users)}")
        print(f"{'ID':<6} {'Email':<35} {'Full Name':<25} {'Role':<10} {'Active':<8}")
        print("-" * 88)
        for u in users:
            name = (u.full_name or "N/A")[:24]
            print(f"{u.id:<6} {u.email:<35} {name:<25} {u.role:<10} {str(u.is_active):<8}")
        print()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Enterprise User Management & RBAC Administration CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    promote_parser = subparsers.add_parser("promote", help="Promote a user to admin role")
    promote_parser.add_argument("email", type=str, help="Email address of user to promote")

    demote_parser = subparsers.add_parser("demote", help="Demote an admin back to standard user role")
    demote_parser.add_argument("email", type=str, help="Email address of user to demote")

    subparsers.add_parser("list", help="List all users with their roles")

    args = parser.parse_args()

    if args.command == "promote":
        promote_user(args.email)
    elif args.command == "demote":
        demote_user(args.email)
    elif args.command == "list":
        list_users()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
