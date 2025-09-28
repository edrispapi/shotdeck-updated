# مسیر: image_service/apps/common/serializers.py
from rest_framework import serializers

class Error401Serializer(serializers.Serializer):
    detail = serializers.CharField(default="Authentication credentials were not provided.")

class Error403Serializer(serializers.Serializer):
    detail = serializers.CharField(default="You do not have permission to perform this action.")
    
class Error404Serializer(serializers.Serializer):
    detail = serializers.CharField(default="Not found.")