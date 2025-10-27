from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'get_full_name',
        'last_login',
    )
    fieldsets = (
        (None, {'fields': ('is_active', 'username',)}),
        (_('Personal info'), {
            'fields': (
                'first_name',
                'last_name',
                'email',
                'cellphone',
            )
        }),
        (_('Notifications'), {
            'fields': (
                'allow_email_notifications', 'allow_push_notifications', 'allow_sms_notifications',
                'allow_whatsapp_notifications',
            ),
        }),
        (_('Admin Permissions'), {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active',)


class GroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'permissions':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            # Avoid a major performance hit resolving permission names which
            # triggers a content_type load:
            kwargs['queryset'] = qs.select_related('content_type')
        return super().formfield_for_manytomany(db_field, request=request, **kwargs)


class CustomGroup(Group):
    class Meta:
        proxy = True
        verbose_name = _("Group")
        verbose_name_plural = _("Groups")


admin.site.unregister(Group)
admin.site.register(User, CustomUserAdmin)
admin.site.register(CustomGroup, GroupAdmin)
