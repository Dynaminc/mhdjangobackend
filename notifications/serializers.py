from rest_framework import serializers


class RegisterDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=4096,
        trim_whitespace=True,
    )

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "A registration token is required."
            )

        return value