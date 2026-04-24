from django.db import models


class Member(models.Model):
    display_name = models.CharField(max_length=150)
    lichess_username = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name
