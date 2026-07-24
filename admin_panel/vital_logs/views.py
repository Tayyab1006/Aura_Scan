from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import UserSession, VitalSignLog
from .serializers import VitalSignLogSerializer, UserSessionSerializer

@api_view(['POST'])
def log_vitals(request):
    """
    Endpoint for FastAPI backend to push vital sign data.
    """
    serializer = VitalSignLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def create_session(request):
    """
    Endpoint to initialize a scan session.
    """
    serializer = UserSessionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
