import os
import xmlschema


class RINFValidator():
    
    def __init__(self):        
        this_dir, this_filename = os.path.split(__file__)
        print(__file__)
        # os.path.split(__file__) : Split the pathname path into a pair
        RINF_SCHEMA_FILE_PATH = os.path.join(this_dir, 'RINFSchema_1.xsd')
        print(this_dir)
        print(this_filename)
        print(RINF_SCHEMA_FILE_PATH)
        self.schema = xmlschema.XMLSchema(RINF_SCHEMA_FILE_PATH)
    
    def validate(self, xml):
        return self.schema.is_valid(xml)
        # xmlschema.XMLSchema :  create a schema instance using the path of the file 
        # containing the schema as argument and returns True of False
        # Source : https://pypi.python.org/pypi/xmlschema/0.9.20

class RINFValidationException(Exception):
    pass