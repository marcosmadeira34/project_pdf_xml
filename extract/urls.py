from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    UploadEProcessarPDFView,
    MergePDFsView,
    TaskStatusView,
    DownloadZipView,
    StreamlitAppRedirectView,
    SendXMLToExternalAPIView,
)


urlpatterns = [
    path("", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("upload-e-processar-pdf/", UploadEProcessarPDFView.as_view(), name="upload-e-processar-pdf"),
    path('merge_pdfs/', MergePDFsView.as_view(), name='merge_pdfs'),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path("download-zip/<str:task_id>/", DownloadZipView.as_view(), name="download-zip"),
    path("streamlit-dashboard/", StreamlitAppRedirectView.as_view(), name="streamlit-dashboard"),
    path("send-xml-to-external-api/", SendXMLToExternalAPIView.as_view(), name="send-xml-to-external-api"),
]