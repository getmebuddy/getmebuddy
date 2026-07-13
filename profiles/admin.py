from django.contrib import admin

from .models import Availability, Interest, InterestChoice, UserProfile

# Register your models here
admin.site.register(Interest)
admin.site.register(InterestChoice)
admin.site.register(UserProfile)
admin.site.register(Availability)
