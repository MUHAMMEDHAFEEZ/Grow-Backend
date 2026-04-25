from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from xp import services
from xp import selectors
from xp.serializers import (
    XPTransactionSerializer,
    XPAddSerializer,
    XPTotalSerializer,
    XPHistorySerializer,
)


class XPAddView(APIView):
    """
    POST /xp/add/
    Add XP to a student's account.
    Used by other apps (assignments, quizzes, attendance).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = XPAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        xp_amount = serializer.validated_data["xp"]
        source = serializer.validated_data["source"]

        try:
            transaction = services.add_xp(request.user, xp_amount, source)
            result = XPTransactionSerializer(transaction)
            return Response(result.data, status=status.HTTP_201_CREATED)

        except services.InvalidXPValueError as e:
            return Response(
                {"error": str(e), "code": "invalid_xp"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except services.InvalidSourceError as e:
            return Response(
                {"error": str(e), "code": "invalid_source"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class XPTotalView(APIView):
    """
    GET /xp/total/
    Get total XP for the authenticated student.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        totals = services.get_total_xp(request.user)
        breakdown = services.get_xp_breakdown(request.user)

        response_data = {
            "total_xp": totals["total_xp"],
            "transaction_count": totals["transaction_count"],
            "breakdown": breakdown,
        }

        serializer = XPTotalSerializer(response_data)
        return Response(serializer.data)


class XPHistoryView(APIView):
    """
    GET /xp/history/
    Get XP transaction history.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        source = request.query_params.get("source", None)

        transactions = selectors.get_xp_history(
            request.user, page=page, page_size=page_size, source=source
        )

        serializer = XPHistorySerializer(transactions, many=True)
        return Response(
            {
                "results": serializer.data,
                "count": selectors.get_total_transactions(request.user),
            }
        )
