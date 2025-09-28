from django.contrib import admin
from usertouser.models import Message

class UserMessages(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'timestamp',)#реализовали отображение полей в админ панеле, не трогая models.py

admin.site.register(Message, UserMessages)