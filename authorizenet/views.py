from django.shortcuts import render_to_response
from django.template import RequestContext
from authorizenet.models import Response
from authorizenet.forms import AIMPaymentForm
from authorizenet.signals import payment_was_successful, payment_was_flagged
from django.http import HttpResponseRedirect

def sim_payment(request):
    response = Response.objects.create_from_dict(request.POST)
    if response.response_code=='1':
        payment_was_successful.send(sender=response)
    else:
        payment_was_flagged.send(sender=response)
    return render_to_response('authorizenet/sim_payment.html', context_instance=RequestContext(request))

class AIMPayment(object):

    processing_error = "There was an error processing your payment. Check your information and try again."
    form_error = "Please correct the errors below and try again."

    def __init__(self, extra_data=None, payment_form_class=AIMPaymentForm, context=None,
                 payment_template="authorizenet/aim_payment.html", success_template='authorizenet/aim_success.html'):
        self.extra_data = extra_data
        self.payment_form_class = payment_form_class
        self.payment_template = payment_template
        self.success_template = success_template
        self.context = context

    def __call__(self, request):
        self.request = request
        if request.method == "GET":
            return self.render_payment_form()
        else:
            return self.validate_payment_form()

    def render_payment_form(self):
        self.context['form'] = self.payment_form_class()
        return render_to_response(self.payment_template, self.context, context_instance=RequestContext(self.request))

    def validate_payment_form(self):
        form = self.payment_form_class(self.request.POST)
        if form.is_valid():
            response = form.process(form.cleaned_data, self.extra_data)
            if response.response_code=='1':
                payment_was_successful.send(sender=response)
                self.context['response'] = response
                return render_to_response(self.success_template, self.context, context_instance=RequestContext(self.request))
            else:
                payment_was_flagged.send(sender=response)
                self.context['errors'] = self.processing_error
        self.context['form'] = form
        self.context.setdefault('errors', self.form_error)
        return render_to_response(self.payment_template, self.context, context_instance=RequestContext(self.request))

