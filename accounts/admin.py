from django.contrib import admin
from .models import Account,UserProfile
from django.contrib.auth.admin  import UserAdmin
from django.utils.html import format_html
class AccountAdmin(UserAdmin):
    list_display = ('email','first_name','last_name','username','last_login','date_joined','is_active')
    list_display_links = ('email', 'first_name', 'last_name')
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

class UserProfileAdmin(admin.ModelAdmin):

    def thumbnail(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%;">',
                obj.profile_picture.url
            )
        return "No Image"

    thumbnail.short_description = "Profile Picture"

    list_display = (
        'thumbnail',
        'user',
        'city',
        'state',
        'country',
    )
admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
