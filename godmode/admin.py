from dataclasses import dataclass, field
from typing import Callable

from typing_extensions import Optional

from django import forms
from django.db import models
from django.template.loader import render_to_string

from users.models.user import User


@dataclass
class ClubAdminField:
    name: str
    display_name: str
    model_field: Optional[models.Field] = None
    list_template: Optional[str] = None

    @classmethod
    def from_model_field(cls, model_field: models.Field):
        return cls(
            name=model_field.name or "Unknown",
            display_name=model_field.verbose_name or model_field.name.replace("_", " ").title(),
            model_field=model_field,
        )

    def render_list(self, value):
        if self.list_template:
            return render_to_string(self.list_template, {
                "value": value,
            })

        try:
            if value is None:
                return ""
            elif hasattr(value, 'strftime'):  # Date/DateTime fields
                return value.strftime('%Y-%m-%d %H:%M')
            elif isinstance(value, bool):
                return "✅" if value else "❌"
            elif hasattr(value, '__str__'):
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 150:
                    str_value = str_value[:150] + "..."
                return str_value
            else:
                return str(value)
        except Exception:
            return "???"


@dataclass
class ClubAdminAction:
    title: str = None
    get: Callable = None
    post: Callable = None

    access_roles: set[str] = field(default_factory=lambda: {User.ROLE_MODERATOR, User.ROLE_GOD})

    def has_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.access_roles or []))


@dataclass
class ClubAdminModel:
    model: type[models.Model] = None
    title: str = None
    icon: str = None
    name: str = None
    title_field: str = None

    list_fields: list | ClubAdminField = field(default_factory=list)
    edit_fields: list = field(default_factory=list)
    hide_fields: list = field(default_factory=list)

    list_roles: set[str] = field(default_factory=lambda: {User.ROLE_MODERATOR, User.ROLE_GOD})
    edit_roles: set[str] = field(default_factory=lambda: {User.ROLE_MODERATOR, User.ROLE_GOD})
    create_roles: set[str] = field(default_factory=lambda: {User.ROLE_GOD})
    delete_roles: set[str] = field(default_factory=lambda: {User.ROLE_GOD})

    actions: dict[str, ClubAdminAction] = field(default_factory=dict)

    def get_absolute_url(self):
        return f"/godmode/{self.name}/" if self.name else None

    def has_list_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.list_roles or []))

    def has_edit_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.edit_roles or []))

    def has_create_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.create_roles or []))

    def has_delete_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.delete_roles or []))

    def get_list_fields(self):
        fields = []
        if self.list_fields:
            for field in self.list_fields:
                if isinstance(field, ClubAdminField):
                    field.model_field = self.model._meta.get_field(field.name)
                    fields.append(field)
                else:
                    fields.append(ClubAdminField.from_model_field(self.model._meta.get_field(field)))
        else:
            fields = [
                ClubAdminField.from_model_field(field)
                for field in self.model._meta.fields
                if field.name not in self.hide_fields
            ]
        return fields

    def get_form_class(self):
        admin_model = self

        class DynamicModelForm(forms.ModelForm):
            class Meta:
                model = admin_model.model
                fields = admin_model.edit_fields if admin_model.edit_fields else [
                    field.name for field in admin_model.model._meta.fields
                    if field.editable and field.name not in admin_model.hide_fields
                ]

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                for field_name, field in self.fields.items():
                    model_field = admin_model.model._meta.get_field(field_name)

                    # Handle foreign key fields - show PK in a text input
                    if isinstance(model_field, models.ForeignKey):
                        field.widget = forms.TextInput()
                        # Set the display value to the related object"s string representation
                        if self.instance and self.instance.pk:
                            related_obj = getattr(self.instance, field_name, None)
                            if related_obj:
                                field.initial = related_obj.pk

                    # Set required based on model constraints
                    if not model_field.null and not model_field.blank and not model_field.has_default():
                        field.required = True
                    else:
                        field.required = False
        return DynamicModelForm


@dataclass
class ClubAdminPage:
    title: str = None
    icon: str = None
    name: str = None

    access_roles: set[str] = field(default_factory=lambda: {User.ROLE_MODERATOR, User.ROLE_GOD})

    view: Callable = None

    def get_absolute_url(self):
        return f"/godmode/page/{self.name}/" if self.name else None

    def has_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.access_roles or []))


@dataclass
class ClubAdminGroup:
    title: str = "Default Group"
    icon: str = ""
    models: list[ClubAdminModel | ClubAdminPage] = field(default_factory=list)


@dataclass
class ClubAdmin:
    title: str = "Admin"
    groups: list[ClubAdminGroup] = field(default_factory=list)
    foreign_key_templates: dict = field(default_factory=dict)

    access_roles: set[str] = field(default_factory=lambda: {User.ROLE_CURATOR, User.ROLE_MODERATOR, User.ROLE_GOD})

    def get_model(self, model_name: str) -> ClubAdminModel | None:
        for group in self.groups:
            for model in group.models:
                if isinstance(model, ClubAdminModel) and model.name == model_name:
                    return model
        return None

    def get_page(self, page_name: str) -> ClubAdminPage | None:
        for group in self.groups:
            for model in group.models:
                if isinstance(model, ClubAdminPage) and model.name == page_name:
                    return model
        return None


    def has_access(self, user: User) -> bool:
        return bool(set(user.roles or []) & set(self.access_roles or []))

