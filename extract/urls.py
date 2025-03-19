from django.urls import path
from .views import LoginView, UploadEProcessarPDFView, MergePDFsView


urlpatterns = [
    path("", LoginView.as_view(), name="login"),
    path("upload-e-processar-pdf/", UploadEProcessarPDFView.as_view(), name="upload-e-processar-pdf"),
    path('merge_pdfs/', MergePDFsView.as_view(), name='merge_pdfs')
]