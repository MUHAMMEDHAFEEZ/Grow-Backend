from rest_framework import serializers
from xp.models import XPTransaction


class XPTransactionSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = XPTransaction
        fields = ["id", "student", "xp_amount", "source", "created_at"]
        read_only_fields = ["id", "student", "created_at"]


class XPAddSerializer(serializers.Serializer):
    """Serializer for adding XP."""

    xp_amount = serializers.IntegerField(min_value=1)
    source = serializers.ChoiceField(choices=XPTransaction.Source.choices)


class XPTotalSerializer(serializers.Serializer):
    """Serializer for total XP response."""

    total_xp = serializers.IntegerField()
    transaction_count = serializers.IntegerField()
    breakdown = serializers.DictField()


class XPHistorySerializer(serializers.ModelSerializer):
    """Serializer for XP transaction history."""

    class Meta:
        model = XPTransaction
        fields = ["id", "student", "xp_amount", "source", "created_at"]
        read_only_fields = fields
