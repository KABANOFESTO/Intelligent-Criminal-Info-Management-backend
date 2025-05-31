from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'profile_picture')

class ProfileUpdateSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    current_password = serializers.CharField(write_only=True, required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = ['username', 'current_password', 'new_password', 'profile_picture']

    def validate(self, data):
        user = self.context['request'].user

        if 'new_password' in data:
            if not user.check_password(data.get('current_password')):
                raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        return data

    def update(self, instance, validated_data):
        if 'username' in validated_data:
            instance.username = validated_data['username']

        if 'new_password' in validated_data:
            instance.set_password(validated_data['new_password'])

        if 'profile_picture' in validated_data:
            # Delete old profile picture if it exists
            if instance.profile_picture:
                instance.profile_picture.delete(save=False)
            instance.profile_picture = validated_data['profile_picture']

        instance.save()
        return instance