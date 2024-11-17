from django.db import models
import uuid
from django.utils import timezone
from dateutil import parser

class client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referral_id = models.CharField(max_length=255, unique=False, editable=True, blank=True, null=True,)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        related_name='referrals',
        db_column='referred_by', blank=True)
    '''

    "db_column=''" Явное указание имени столбца, используемого в базе данных
    
    '''

    telegramid = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    firstname = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=True, null=True)
    phonenumber = models.CharField(max_length=15, blank=True, null=True)
    UsedTestSubscription = models.BooleanField(default=False)
    usedref = models.BooleanField(default=False)
    '''

    "db table = ''" Заствляет джанго использовать уже существующие модели в бд
    после makemigrations необходимо сделать "фейковую" миграцию бд, без её миграции на самом деле:
    python manage.py migrate --fake

    '''

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4())  # Ensure a UUID is set if not provided
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'client'
        verbose_name = 'Клиент'  # Меняет название вытягиваемое из дб, на любое другое
        verbose_name_plural = 'Клиенты' # В множ. числе

    def to_dict(self):
        return {
            'id': self.id,
            'telegramid': self.telegramid,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname
        }
    
    def __str__(self):
        # Получаем название тарифа
        first_subscription = self.subscriptions.first()
        if first_subscription and first_subscription.rateid:
            rate_name = first_subscription.rateid.name
            return f"{self.username} ({rate_name})"# Для корректного отображения Имя пользователя в админке
        else:
            return f"{self.username} (Нет активного тарифа)" 
        
        
class rate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    dayamount = models.IntegerField()
    price = models.IntegerField()
    isreferral = models.BooleanField(default=False)
    bonus_days = models.IntegerField(null=True, blank=True)


    class Meta:
        db_table = 'rate'
        verbose_name = 'Тариф'  
        verbose_name_plural = 'Тарифы'

    def __str__(self):
        return self.name
    

class subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clientid = models.ForeignKey(
        client, 
        on_delete=models.CASCADE, 
        related_name='subscriptions', 
        db_column='clientid')
    
    rateid = models.ForeignKey(
        rate, 
        on_delete=models.CASCADE, 
        related_name='subscriptions', 
        db_column='rateid')

    name = models.CharField(max_length=255, blank=True, null=True)
    
    datestart = models.DateTimeField()
    dateend = models.DateTimeField()
    public_key = models.CharField(max_length=255, null=True, blank=True)
    config_name = models.CharField(max_length=255, null=True, blank=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'subscription'
        verbose_name = 'Подписка'  
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"{self.clientid.username} - {self.rateid.name}"

    def save(self, *args, **kwargs):
        # Handle dateend if it is a string
        if isinstance(self.dateend, str):
            try:
                self.dateend = parser.parse(self.dateend)
            except ValueError as e:
                raise ValueError(f"Invalid date format for dateend: {e}")

        # Ensure dateend is timezone-aware
        if self.dateend and not self.dateend.tzinfo:
            self.dateend = timezone.make_aware(self.dateend, timezone.get_current_timezone())
        
        # Save the subscription
        super().save(*args, **kwargs)

class codes(models.Model):
    code = models.CharField(max_length=255, blank=True, null=True)
    used_code = models.BooleanField(default=False)

    class Meta:
        db_table = 'codes'
        verbose_name = 'Уникальный код'  
        verbose_name_plural = 'Уникальные коды'

    