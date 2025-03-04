from django.contrib import admin
from .models import Interest, InterestChoice, UserProfile, Availability

# Register your models here
admin.site.register(Interest)
admin.site.register(InterestChoice)
admin.site.register(UserProfile)
admin.site.register(Availability)