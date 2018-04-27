from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import Document
from .forms import DocumentForm
from .lib.rinf_validator.validator import RINFValidator, RINFValidationException
from .lib.rinf_to_sql import rinf_to_sql
from .lib.rinf_to_sql.rinf_to_postgres import RINFExtractor,RINFExtractorConfig

class HomeView(TemplateView):
    template_name = "home.html"

def model_form_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            validator = RINFValidator()
            xml = request.FILES['document'].read().decode('utf-8')

            if validator.validate(xml):               
                new_document = form.save()
                input_file = request.FILES['document'].open()
                config = RINFExtractorConfig(
                    'localhost',
                    '5433',
                    'postgres',
                    '12345678',
                    'geodjango_test'
                )
                rinf_extractor = RINFExtractor(config)
                rinf_extractor.parse_xml(input_file)
                rinf_extractor.close()                  
            else:
                with open('debug.xml', 'w') as f:
                    f.write(xml)
                raise RINFValidationException('file failed RINF validation!')                
                
    else:
        form = DocumentForm()
    return render(request, 'upload.html', {
        'form': form
    })



"""
class FileFieldView(FormView):
    form_class = DocumentForm
    template_name = 'upload.html'  # Replace with your template.
    success_url = 'documents/'  # Replace with your URL or reverse().

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file_field')
        if form.is_valid():
            for f in files:
                ...  # Do something with each file.
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
            
"""