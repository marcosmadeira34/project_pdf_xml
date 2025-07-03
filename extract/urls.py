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
from .auth_views import (
    AuthLoginView,
    AuthRefreshView,
    AuthVerifyView,
    AuthLogoutView,
    AuthUserInfoView,
)
from .credit_views import (
    CreditsInfoView,
    CreditPackagesView,
    CreatePaymentOrderView,
    ConfirmPaymentView,
    PaymentOrderStatusView,
)

urlpatterns = [
    path("", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("upload-e-processar-pdf/", UploadEProcessarPDFView.as_view(), name="upload-e-processar-pdf"),
    path('merge_pdfs/', MergePDFsView.as_view(), name='merge_pdfs'),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path("download-zip/<uuid:task_id>/", DownloadZipView.as_view(), name="download-zip"),
    path("streamlit-dashboard/", StreamlitAppRedirectView.as_view(), name="streamlit-dashboard"),
    path("send-xml-to-external-api/", SendXMLToExternalAPIView.as_view(), name="send-xml-to-external-api"),
    
    # Endpoints de autenticação JWT
    path("auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("auth/refresh/", AuthRefreshView.as_view(), name="auth-refresh"),
    path("auth/verify/", AuthVerifyView.as_view(), name="auth-verify"),    # No shell do Django:
    
    path("auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("auth/user-info/", AuthUserInfoView.as_view(), name="auth-user-info"),
    
    # Endpoints de créditos
    path("credits/info/", CreditsInfoView.as_view(), name="credits-info"),
    path("credits/packages/", CreditPackagesView.as_view(), name="credit-packages"),
    path("credits/create-payment/", CreatePaymentOrderView.as_view(), name="create-payment-order"),
    path("credits/confirm-payment/", ConfirmPaymentView.as_view(), name="confirm-payment"),
    path("credits/payment-status/<uuid:order_id>/", PaymentOrderStatusView.as_view(), name="payment-order-status"),
]