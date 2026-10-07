from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """`User.objects` — knows how to create users with a hashed password."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes; None -> unusable password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Django's standard user, with email instead of username as the login."""

    username = None  # remove the inherited field
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"   # what authenticate() / SimpleJWT log in with
    REQUIRED_FIELDS = []       # extra prompts for `createsuperuser`

    objects = UserManager()

    def __str__(self):
        return self.email
