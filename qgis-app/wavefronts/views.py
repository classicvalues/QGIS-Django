import os
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from base.views.processing_view import (ResourceBaseCreateView,
                                        ResourceBaseDetailView,
                                        ResourceBaseUpdateView,
                                        ResourceBaseListView,
                                        ResourceBaseUnapprovedListView,
                                        ResourceBaseRequireActionListView,
                                        ResourceBaseDeleteView,
                                        ResourceBaseReviewView,
                                        ResourceBaseDownload,
                                        resource_nav_content)

from base.views.processing_view import check_resources_access, resource_notify

from wavefronts.forms import UpdateForm, UploadForm
from wavefronts.models import Wavefront, Review
from wavefronts.utilities import zipped_all_with_license


class ResourceMixin():
    """Mixin class for Wavefront."""

    model = Wavefront

    review_model = Review

    # The resource_name will be displayed as the app name on web page
    resource_name = '3D Model'

    # The url name in urls.py should start with this value
    resource_name_url_base = 'wavefront'


class WavefrontCreateView(ResourceMixin, ResourceBaseCreateView):
    """Upload a Wavefront File"""

    form_class = UploadForm
    is_1mb_limit_enable = False

    def form_valid(self, form):
        self.obj = form.save(commit=False)
        self.obj.creator = self.request.user
        self.obj.file.name = form.file_path
        self.obj.save()
        resource_notify(self.obj, resource_type=self.resource_name)
        msg = _(self.success_message)
        messages.success(self.request, msg, 'success', fail_silently=True)
        return super(ResourceBaseCreateView, self).form_valid(form)


class WavefrontDetailView(ResourceMixin, ResourceBaseDetailView):
    """Wavefront Detail View"""

    is_3d_model = True
    js = (
        {'src': 'wavefront/js/3d_view.js', 'type': 'module'},
    )
    css = ('wavefront/css/wavefront.css',)

    def get_context_data(self, **kwargs):
        context = super(WavefrontDetailView, self).get_context_data()
        obj = self.get_object()
        filename, ext = os.path.splitext(obj.file.url)
        context['obj_url'] = f'{filename}.obj'
        context['mtl_url'] = f'{filename}.mtl'
        return context


class WavefrontUpdateView(ResourceMixin, ResourceBaseUpdateView):
    """Update the Wavefront"""

    form_class = UpdateForm

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.file.name = form.file_path
        obj.require_action = False
        obj.approved = False
        obj.save()
        resource_notify(obj, created=False, resource_type=self.resource_name)
        msg = _("The %s has been successfully updated." % self.resource_name)
        messages.success(self.request, msg, 'success', fail_silently=True)
        url_name = '%s_detail' % self.resource_name_url_base
        return HttpResponseRedirect(reverse_lazy(url_name,
                                                 kwargs={'pk': obj.id}))


class WavefrontListView(ResourceMixin, ResourceBaseListView):
    """Approved Wavefront ListView"""


class WavefrontUnapprovedListView(ResourceMixin,
                                   ResourceBaseUnapprovedListView):
    """Unapproved Wavefront ListView"""


class WavefrontRequireActionListView(ResourceMixin,
                                      ResourceBaseRequireActionListView):
    """Wavefront Requires Action"""


class WavefrontDeleteView(ResourceMixin, ResourceBaseDeleteView):
    """Delete a Wavefront."""


class WavefrontReviewView(ResourceMixin, ResourceBaseReviewView):
    """Create a review"""


class WavefrontDownloadView(ResourceMixin, ResourceBaseDownload):
    """Download a Wavefront"""

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        if not object.approved:
            if not check_resources_access(self.request.user, object):
                context = super(ResourceBaseDownload, self).get_context_data()
                context['object_name'] = object.name
                context['context'] = ('Download failed. This %s is '
                                      'not approved' % self.resource_name)
                return TemplateResponse(request, self.template_name, context)
        else:
            object.increase_download_counter()
            object.save()

        # zip the 3d files folder and license.txt
        path, filename = os.path.split(object.file.file.name)
        zipfile = zipped_all_with_license(path, object.name)

        response = HttpResponse(
            zipfile.getvalue(), content_type="application/x-zip-compressed")
        response['Content-Disposition'] = 'attachment; filename=%s.zip' % (
            slugify(object.name, allow_unicode=True)
        )
        return response


def wavefront_nav_content(request):
    model = ResourceMixin.model
    response = resource_nav_content(request, model)
    return response
