from rinf_validator.validator import RINFValidator

validator = RINFValidator()

with open('/home/kardelen/work/test_apps/django-importXML/XMLimporter/debug.xml') as f:
    data = f.read()
    validator.validate(data)

