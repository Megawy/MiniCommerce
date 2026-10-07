from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # The base UserAdmin references `username`; swap it for `email`.
    add_form = UserCreateForm
    form = UserEditForm
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_staff", "is_active", "date_joined", "last_login"]
    # list_filter is inherited: is_staff, is_superuser, is_active, groups
    search_fields = ["email", "first_name", "last_name"]  # also powers autocomplete (Cart.user)
    date_hierarchy = "date_joined"
    readonly_fields = ["last_login", "date_joined"]
    fieldsets = (
        # "password" renders Django's ReadOnlyPasswordHashField: a masked summary plus a
        # "Reset password" link — never the editable hash.
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
