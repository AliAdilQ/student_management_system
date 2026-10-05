from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
            if isinstance(widget, forms.Textarea):
                widget.attrs["rows"] = 3
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(
                    attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
                )
            if isinstance(field, forms.DecimalField):
                widget.attrs["step"] = "0.01"


class RecordForm(StyledFormMixin, forms.ModelForm):
    def clean(self):
        data = super().clean()
        if "subjects" in data and data.get("course"):
            if any(
                s.course_id != data["course"].pk or s.semester != data.get("semester")
                for s in data["subjects"]
            ):
                self.add_error(
                    "subjects",
                    "Subjects must match the enrollment's course and semester.",
                )
        return data


class LoginForm(StyledFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "The username or password is incorrect. Please try again.",
        "inactive": "This account is inactive. Contact your administrator.",
    }


class AccountCreateForm(StyledFormMixin, UserCreationForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=["Registrar", "Faculty", "Viewer"]),
        empty_label=None,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.groups.set([self.cleaned_data["role"]])
        return user


class AccountUpdateForm(StyledFormMixin, forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=["Registrar", "Faculty", "Viewer"]),
        required=False,
        empty_label="Custom permissions / superuser",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["role"].initial = self.instance.groups.first()

    def clean_is_active(self):
        active = self.cleaned_data["is_active"]
        if (
            not active
            and self.instance.is_superuser
            and not User.objects.filter(is_superuser=True, is_active=True)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("At least one active superuser must remain.")
        return active

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.groups.set(
                [self.cleaned_data["role"]] if self.cleaned_data.get("role") else []
            )
        return user
