from django import forms
from django.core.exceptions import ValidationError

from .models import ContactMessage, Member, UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('lichess_username', 'lichess_api_key')
        widgets = {
            'lichess_api_key': forms.PasswordInput(render_value=True, attrs={'placeholder': 'Paste your Lichess API token'}),
            'lichess_username': forms.TextInput(attrs={'placeholder': 'your_lichess_username'}),
        }


class MemberProfileForm(forms.ModelForm):
    avatar_max_mb = 4

    class Meta:
        model = Member
        fields = ('display_name', 'avatar')
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/jpeg,image/png,image/webp,image/gif',
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False
        self.fields['avatar'].help_text = (
            f'JPEG, PNG, WebP, or GIF. Maximum file size roughly {self.avatar_max_mb} MB. '
            'Clear the checkbox below to remove the current photo.'
        )

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and getattr(avatar, 'size', 0):
            limit = self.avatar_max_mb * 1024 * 1024
            if avatar.size > limit:
                raise ValidationError(
                    f'Please use an image under {self.avatar_max_mb} MB.',
                    code='avatar_too_large',
                )
        return avatar


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'body')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
