from rest_framework import serializers
from .models import client, rate, subscription, codes

class clientSerializer(serializers.ModelSerializer):
    class Meta:
        model = client
        fields = '__all__'

class codesSerializer(serializers.ModelSerializer):
    class Meta:
        model = codes
        fields = '__all__'

class rateSerializer(serializers.ModelSerializer):
    class Meta:
        model = rate
        fields = ['id', 'name', 'dayamount', 'price', 'isreferral', 'bonus_days']

class subscriptionSerializer(serializers.ModelSerializer):
    clientid = serializers.PrimaryKeyRelatedField(queryset=client.objects.all())
    rateid = serializers.PrimaryKeyRelatedField(queryset=rate.objects.all())

    class Meta:
        model = subscription
        fields = ('id', 'datestart', 'dateend', 'clientid', 'rateid', 'name', 'is_used')

    def create(self, validated_data):
        print(f"Creating subscription with data: {validated_data}")
        client_instance = validated_data.pop('clientid')
        rate_instance = validated_data.pop('rateid')

        subscription_instance = subscription.objects.create(
            clientid=client_instance,
            rateid=rate_instance,
            **validated_data
        )
        print(f"Subscription created: {subscription_instance}")
        return subscription_instance