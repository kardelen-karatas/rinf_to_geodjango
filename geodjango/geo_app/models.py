# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models
#from __future__ import unicode_literals

class Document(models.Model):
    doc_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, blank=True)
    document = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'document'

class Member(models.Model):
    mem_id = models.CharField(primary_key=True, max_length=255)
    mem_version = models.CharField(max_length=255, blank=True, null=True)
    doc_id = models.ForeignKey(Document, on_delete=models.CASCADE, blank=True, null=True)
   
    class Meta:
        managed = True
        db_table = 'member'

class Line(models.Model):
    lin_id = models.CharField(primary_key=True, max_length=255)
    lin_name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    mem = models.ForeignKey('Member', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'line'

class OpType(models.Model):
    oty_id = models.IntegerField(primary_key=True)
    oty_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'op_type'

class OperationalPoint(models.Model):
    opp_id = models.CharField(primary_key=True, max_length=255)
    opp_name = models.CharField(max_length=255, blank=True, null=True)
    opp_uniqueid = models.CharField(unique=True, max_length=255, blank=True, null=True)
    opp_lon = models.FloatField(blank=True, null=True)
    opp_lat = models.FloatField(blank=True, null=True)
    geom = models.PointField(blank=True, null=True)
    opp_taftapcode = models.CharField(max_length=255, blank=True, null=True)
    opp_date_start = models.DateField(blank=True, null=True)
    opp_date_end = models.DateField(blank=True, null=True)
    opp_track_nb = models.IntegerField(blank=True, null=True)
    opp_tunnel_nb = models.IntegerField(blank=True, null=True)
    opp_platform_nb = models.IntegerField(blank=True, null=True)
    oty_id = models.ForeignKey(OpType, on_delete=models.CASCADE, blank=True, null=True)
    mem_id = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'operational_point'

class OppParameterValue(models.Model):
    opv_id = models.AutoField(primary_key=True)
    opv_value = models.CharField(max_length=255, blank=True, null=True)
    opp_id = models.ForeignKey(OperationalPoint, on_delete=models.CASCADE, blank=True, null=True)
    par_name = models.ForeignKey('Parameter', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'opp_parameter_value'
        unique_together = (('opp_id', 'par_name', 'opv_value'),)

class Parameter(models.Model):
    TYPE_CHOICES = (
        (1,'TRACK'),
        (2,'SOL_TRACK'),
        (3,'TUNNEL'),
        (4,'PLATFORM'),
    )
       
    par_id = models.CharField(primary_key=True, max_length=255)
    par_name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    par_type = models.CharField(max_length=254, choices=TYPE_CHOICES) 

    class Meta:
        managed = True
        db_table = 'parameter'

class ParameterDefinition(models.Model):
    ppv_id = models.AutoField(primary_key=True)
    par_name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    ppv_value = models.CharField(max_length=255, blank=True, null=True)
    ppv_optional_value = models.CharField(max_length=255, blank=True, null=True)
    par = models.ForeignKey(Parameter, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'parameter_definition'


class SectionOfLine(models.Model):
    sol_id = models.CharField(primary_key=True, max_length=255)
    sol_length = models.FloatField(blank=True, null=True)
    sol_nature = models.CharField(max_length=255, blank=True, null=True)
    sol_imcode = models.CharField(max_length=255, blank=True, null=True)
    sol_date_start = models.DateField(blank=True, null=True)
    sol_date_end = models.DateField(blank=True, null=True)
    sol_track_nb = models.IntegerField(blank=True, null=True)
    sol_tunnel_nb = models.IntegerField(blank=True, null=True)
    opp_start = models.ForeignKey(OperationalPoint, on_delete=models.CASCADE, related_name='opp_start', blank=True, null=True)
    opp_end = models.ForeignKey(OperationalPoint, on_delete=models.CASCADE, related_name='opp_end', blank=True, null=True)
    mem = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)
    lin = models.ForeignKey(Line, on_delete=models.CASCADE, blank=True, null=True)
   
    class Meta:
        managed = True
        db_table = 'section_of_line'
        unique_together = (('opp_start', 'opp_end'),)


class SolParameterValue(models.Model):
    spv_id = models.AutoField(primary_key=True)
    spv_value = models.CharField(max_length=255, blank=True, null=True)
    sol = models.ForeignKey(SectionOfLine, on_delete=models.CASCADE)
    par_name = models.ForeignKey(Parameter, on_delete=models.CASCADE)

    class Meta:
        managed = True
        db_table = 'sol_parameter_value'
        unique_together = (('sol', 'par_name', 'spv_value'),)