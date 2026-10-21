from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.update(is_superuser=True, is_staff=True, is_active=True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="user_email_lower_unique")]
        permissions = [
            ("manage_accounts", "Quản lý tài khoản và phân quyền"),
            ("manage_sales", "Xử lý đơn và bán tại quầy"),
            ("manage_payments", "Thu và hoàn tiền"),
            ("manage_stock", "Ghi sổ và điều chuyển kho"),
            ("view_reports", "Xem báo cáo"),
            ("view_audit", "Xem nhật ký nghiệp vụ"),
            ("manage_people", "Quản lý hồ sơ trong chi nhánh"),
        ]


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="employee")
    code = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    title = models.CharField(max_length=150, blank=True)


class RoleAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assignments")
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    store = models.ForeignKey("stores.Store", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "group", "store"], name="unique_branch_role")
        ]


class SocialIdentity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)
    subject = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "subject"], name="social_provider_subject")
        ]


class ResetChallenge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GoogleLoginAttempt(models.Model):
    """Five-minute, single-use OAuth state, bound to the initiating browser session."""

    state_hash = models.CharField(max_length=64, primary_key=True)
    session_hash = models.CharField(max_length=64)
    nonce = models.CharField(max_length=128)
    code_verifier = models.CharField(max_length=128)
    redirect_uri = models.URLField(max_length=500)
    next_path = models.CharField(max_length=500, blank=True)
    link_account = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True)


class FacebookLoginAttempt(models.Model):
    """Single-use Facebook code flow state, bound to a browser and optional account."""

    state_hash = models.CharField(max_length=64, primary_key=True)
    session_hash = models.CharField(max_length=64)
    redirect_uri = models.URLField(max_length=500)
    next_path = models.CharField(max_length=500, blank=True)
    link_account = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True)
