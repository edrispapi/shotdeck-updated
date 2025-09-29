from rest_framework import serializers

class Error404Serializer(serializers.Serializer):
    detail = serializers.CharField(default="Not found.")