import functools

from django.urls import include, re_path

from wagtail.utils.urlpatterns import decorate_urlpatterns


class WagtailAPIRouter:
    """
    A class that provides routing and cross-linking for a collection
    of API endpoints
    """

    def __init__(self, url_namespace):
        self.url_namespace = url_namespace
        self._endpoints = {}
        self._model2endpoint = {}

    def register_endpoint(self, name, class_, as_default_view=True):
        """
        Registers the endpoint's URLs under the provided name as namespace.

        If `as_default_view` is set (the default), then the endpoint
        will be used for reverse resolution in :meth:`get_model_listing_urlpath`
        and :meth:`get_object_detail_urlpath` (e.g. in `detail_url` field on objects).
        """
        self._endpoints[name] = class_
        if as_default_view and class_.model is not None:
            # setdefault instead of assign so first takes precedence,
            # like now
            self._model2endpoint.setdefault(class_.model, (name, class_))

    def get_model_endpoint(self, model, specific=False):
        """
        Finds the endpoint in the API that represents a model

        Returns a (name, endpoint_class) tuple. Or None if an
        endpoint is not found.
        """
        for class_ in model.__mro__:
            if class_ in self._model2endpoint:
                return self._model2endpoint[class_]

    def get_model_listing_urlpath(self, model):
        """
        Returns a URL path (excluding scheme and hostname) to the listing
        page of a model

        Returns None if the model is not represented by any endpoints.
        """
        endpoint = self.get_model_endpoint(model)

        if endpoint:
            endpoint_name, endpoint_class = endpoint[0], endpoint[1]
            url_namespace = self.url_namespace + ":" + endpoint_name
            return endpoint_class.get_model_listing_urlpath(
                model, namespace=url_namespace
            )

    def get_object_detail_urlpath(self, model, pk):
        """
        Returns a URL path (excluding scheme and hostname) to the detail
        page of an object.

        Returns None if the object is not represented by any endpoints.
        """
        endpoint = self.get_model_endpoint(model)

        if endpoint:
            endpoint_name, endpoint_class = endpoint[0], endpoint[1]
            url_namespace = self.url_namespace + ":" + endpoint_name
            return endpoint_class.get_object_detail_urlpath(
                model, pk, namespace=url_namespace
            )

    def wrap_view(self, func):
        @functools.wraps(func)
        def wrapped(request, *args, **kwargs):
            request.wagtailapi_router = self
            return func(request, *args, **kwargs)

        return wrapped

    def get_urlpatterns(self):
        urlpatterns = []

        for name, class_ in self._endpoints.items():
            pattern = re_path(
                rf"^{name}/",
                include((class_.get_urlpatterns(), name), namespace=name),
            )
            urlpatterns.append(pattern)

        decorate_urlpatterns(urlpatterns, self.wrap_view)

        return urlpatterns

    @property
    def urls(self):
        """
        A shortcut to allow quick registration of the API in a URLconf.

        Use with Django's include() function:

            path('api/', include(myapi.urls)),
        """
        return self.get_urlpatterns(), self.url_namespace, self.url_namespace
