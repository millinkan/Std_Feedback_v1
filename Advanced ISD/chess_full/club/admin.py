from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'lichess_username')
    search_fields = ('display_name', 'lichess_username')
