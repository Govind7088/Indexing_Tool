from django.urls import path

from .views import AllURLListView, RecentURLListView, URLSubmissionCreateView, URLRecheckView


urlpatterns = [
    path('urls/', URLSubmissionCreateView.as_view(), name='url-list'),
    path('urls/recent/', RecentURLListView.as_view(), name='recent-urls'),
    path('urls/all/', AllURLListView.as_view(), name='all-urls'),
    path('urls/<int:pk>/recheck/', URLRecheckView.as_view(), name='url-recheck'),
]