from django import forms
from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()


class SignUpForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "password", "role"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user


class AddStudentForm(forms.ModelForm):

    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Student
        fields = ["name", "age", "grade"]

    def save(self, parent, commit=True):

        username = self.cleaned_data["username"]
        password = self.cleaned_data["password"]
        name = self.cleaned_data["name"]
        age = self.cleaned_data["age"]
        grade = self.cleaned_data["grade"]

        user = User.objects.create_user(
            username=username,
            password=password,
            role="student"
        )

        student = Student.objects.create(
            user=user,
            parent=parent,
            name=name,
            age=age,
            grade=grade
        )

        return student