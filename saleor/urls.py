from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.views import serve
from django.views.i18n import JavaScriptCatalog, set_language
from graphene_django.views import GraphQLView

from .account.urls import urlpatterns as account_urls
from .cart.urls import urlpatterns as cart_urls
from .checkout.urls import urlpatterns as checkout_urls
from .core.sitemaps import sitemaps
from .core.urls import urlpatterns as core_urls
from .dashboard.urls import urlpatterns as dashboard_urls
from .data_feeds.urls import urlpatterns as feed_urls
from .graphql.api import schema
from .order.urls import urlpatterns as order_urls
from .page.urls import urlpatterns as page_urls
from .product.urls import urlpatterns as product_urls
from .search.urls import urlpatterns as search_urls

handler404 = 'saleor.core.views.handle_404'

non_translatable_urlpatterns = [
    url(r'^dashboard/',
        include((dashboard_urls, 'dashboard'), namespace='dashboard')),
    url(r'^graphql', GraphQLView.as_view(
        schema=schema, graphiql=settings.DEBUG), name='api'),
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    url(r'^i18n/$', set_language, name='set_language')]

translatable_urlpatterns = [
    url(r'^', include(core_urls)),
    url(r'^cart/', include((cart_urls, 'cart'), namespace='cart')),
    url(r'^checkout/',
        include((checkout_urls, 'checkout'), namespace='checkout')),
    url(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'^order/', include((order_urls, 'order'), namespace='order')),
    url(r'^page/', include((page_urls, 'page'), namespace='page')),
    url(r'^products/',
        include((product_urls, 'product'), namespace='product')),
    url(r'^account/',
        include((account_urls, 'account'), namespace='account')),
    url(r'^feeds/',
        include((feed_urls, 'data_feeds'), namespace='data_feeds')),
    url(r'^search/', include((search_urls, 'search'), namespace='search')),
    url(r'', include('payments.urls')),
    url('', include('social_django.urls', namespace='social'))]

urlpatterns = non_translatable_urlpatterns + i18n_patterns(
    *translatable_urlpatterns)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', serve)] + static(
            settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

if settings.ENABLE_SILK:
    urlpatterns += [
        url(r'^silk/', include('silk.urls', namespace='silk'))
    ]
