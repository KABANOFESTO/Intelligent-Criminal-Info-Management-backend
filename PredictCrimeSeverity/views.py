from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import joblib
import pandas as pd
from .models import CrimePrediction
from .serializers import CrimePredictionInputSerializer, CrimePredictionSerializer
from rest_framework.generics import RetrieveAPIView, ListAPIView
from django.db.models import Count, Q

class PredictCrimeSeverity(APIView):
    def post(self, request):
        try:
            # Validate input data
            input_serializer = CrimePredictionInputSerializer(data=request.data)
            if not input_serializer.is_valid():
                return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = input_serializer.validated_data
            crime_type = validated_data['crime_type']
            lat = validated_data['latitude']
            lon = validated_data['longitude']

            # Load model and encoder
            model = joblib.load("ml/crime_severity_model.pkl")
            encoder = joblib.load("ml/crime_label_encoder.pkl")

            try:
                encoded_crime_type = encoder.transform([crime_type])[0]
            except ValueError:
                return Response({"error": "Unknown crime type"}, status=status.HTTP_400_BAD_REQUEST)

            # Create input DataFrame for prediction
            input_df = pd.DataFrame([{
                "crime_type_encoded": encoded_crime_type,
                "Latitude": lat,
                "Longitude": lon
            }])

            # Make prediction
            prediction_value = model.predict(input_df)[0]
            predicted_severity = "Severe" if prediction_value == 1 else "Not Severe"

            # Save to database
            crime_prediction = CrimePrediction.objects.create(
                crime_type=crime_type,
                latitude=lat,
                longitude=lon,
                encoded_crime_type=int(encoded_crime_type),
                predicted_severity=predicted_severity,
                prediction_value=int(prediction_value)
            )

            # Serialize and return the saved data
            serializer = CrimePredictionSerializer(crime_prediction)
            
            return Response({
                "predicted_severity": predicted_severity,
                "prediction_id": crime_prediction.id,
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """Optional: Get all predictions or filter by parameters"""
        predictions = CrimePrediction.objects.all()
        
        # Optional filtering
        crime_type = request.query_params.get('crime_type')
        severity = request.query_params.get('severity')
        
        if crime_type:
            predictions = predictions.filter(crime_type__icontains=crime_type)
        if severity:
            predictions = predictions.filter(predicted_severity=severity)
            
        serializer = CrimePredictionSerializer(predictions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class CrimePredictionDetailView(RetrieveAPIView):
    """Get a specific prediction by ID"""
    queryset = CrimePrediction.objects.all()
    serializer_class = CrimePredictionSerializer

class CrimePredictionListView(ListAPIView):
    """Get predictions with filtering and statistics"""
    queryset = CrimePrediction.objects.all()
    serializer_class = CrimePredictionSerializer
    
    def get_queryset(self):
        queryset = CrimePrediction.objects.all()
        
        # Filter parameters
        crime_type = self.request.query_params.get('crime_type')
        severity = self.request.query_params.get('severity')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if crime_type:
            queryset = queryset.filter(crime_type__icontains=crime_type)
        if severity:
            queryset = queryset.filter(predicted_severity=severity)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        # Add statistics to response
        response = super().list(request, *args, **kwargs)
        
        # Get statistics
        total_predictions = CrimePrediction.objects.count()
        severe_count = CrimePrediction.objects.filter(predicted_severity='Severe').count()
        not_severe_count = CrimePrediction.objects.filter(predicted_severity='Not Severe').count()
        
        # Crime type distribution
        crime_type_stats = CrimePrediction.objects.values('crime_type').annotate(
            count=Count('id')
        ).order_by('-count')[:10]  # Top 10 crime types
        
        response.data = {
            'statistics': {
                'total_predictions': total_predictions,
                'severe_predictions': severe_count,
                'not_severe_predictions': not_severe_count,
                'severity_percentage': {
                    'severe': round((severe_count / total_predictions * 100) if total_predictions > 0 else 0, 2),
                    'not_severe': round((not_severe_count / total_predictions * 100) if total_predictions > 0 else 0, 2)
                },
                'top_crime_types': list(crime_type_stats)
            },
            'results': response.data
        }
        
        return response