import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.base import TemplateView, View
from ledger_api_client.helpers import is_payment_admin
from ledger_api_client.ledger_models import EmailUserRO as EmailUser
from ledger_api_client.ledger_models import Invoice, Basket
from ledger_api_client.utils import validate_booking_and_invoice_references
from rest_framework import serializers, status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from commercialoperator.components.bookings.confirmation_pdf import (
    create_confirmation_pdf_bytes,
)
from commercialoperator.components.bookings.context_processors import template_context
from commercialoperator.components.bookings.email import (
    send_application_fee_invoice_tclass_email_notification,
    send_compliance_fee_invoice_events_email_notification,
    send_confirmation_tclass_email_notification,
    send_invoice_tclass_email_notification,
)
from commercialoperator.components.bookings.models import (
    ApplicationFee,
    ApplicationFeeInvoice,
    Booking,
    BookingInvoice,
    ComplianceFee,
    ComplianceFeeInvoice,
    FilmingFee,
    FilmingFeeInvoice,
    ParkBooking,
)
from commercialoperator.components.bookings.monthly_confirmation_pdf import (
    create_monthly_confirmation_pdf_bytes,
)
from commercialoperator.components.bookings.utils import (
    checkout,
    checkout_existing_invoice,
    create_booking,
    create_bpay_invoice,
    create_compliance_fee_lines,
    create_fee_lines,
    create_lines,
    create_monthly_confirmation,
    create_other_invoice,
    delete_session_booking,
    get_invoice_pdf,
    get_invoice_properties,
    get_session_application_invoice,
    get_session_booking,
    get_session_compliance_invoice,
    get_session_filming_invoice,
    set_session_application_invoice,
    set_session_booking,
    set_session_compliance_invoice,
    set_session_filming_invoice,
)
from commercialoperator.components.compliances.models import Compliance
from commercialoperator.components.main.models import ApplicationType
from commercialoperator.components.organisations.models import (
    Organisation,
    OrganisationContact,
)
from commercialoperator.components.proposals.models import Proposal
from commercialoperator.components.proposals.utils import proposal_submit
from commercialoperator.helpers import is_in_organisation_contacts, is_internal

logger = logging.getLogger("payment_checkout")


class ApplicationFeeView(TemplateView):
    template_name = "commercialoperator/booking/success.html"

    def get_object(self):
        return get_object_or_404(Proposal, id=self.kwargs["proposal_pk"])

    def post(self, request, *args, **kwargs):
        application_fee = None
        try:
            proposal = self.get_object()

            user = request.user
            try:
                user_orgs = [
                    org.id for org in user.commercialoperator_organisations.all()
                ]
                if not (
                    is_internal(self.request)
                    or proposal.org_applicant_id in user_orgs
                    or proposal.submitter == user
                ):
                    raise PermissionDenied
            except:
                raise

            if proposal.is_amendment_proposal:
                raise PermissionDenied(
                    "No application fee is payable for an amendment application."
                )

            if request.user and isinstance(request.user, EmailUser):
                if not proposal.submitter:
                    proposal.submitter = (
                        request.user
                    )  # NOTE: submitter should already be set
                    proposal.save()
                # Same org, different submitter
                if proposal.org_applicant:
                    if OrganisationContact.objects.filter(
                        organisation=proposal.org_applicant, email=request.user.email
                    ).exists():
                        proposal.submitter = request.user
                        proposal.save()

            application_fee = ApplicationFee.objects.create(
                proposal=proposal,
                created_by=request.user,
                payment_type=ApplicationFee.PAYMENT_TYPE_TEMPORARY,
            )

            with transaction.atomic():
                lines = create_fee_lines(proposal)

                set_session_application_invoice(request.session, application_fee)
                return_url = request.build_absolute_uri(
                    reverse(
                        "fee_success", kwargs={"reference": proposal.lodgement_number}
                    )
                )
                return_preload_url = settings.COMMERCIALOPERATOR_EXTERNAL_URL + reverse(
                    "fee_success_preload",
                    kwargs={"reference": proposal.lodgement_number},
                )
                checkout_response = checkout(
                    request,
                    proposal,
                    lines,
                    return_url,
                    return_preload_url,
                    invoice_text="Application Fee",
                    reference=proposal.lodgement_number,
                )

                # Set session variables
                request.session["payment_pk"] = proposal.pk
                request.session["payment_model"] = "proposal"

                logger.info(
                    "{} built payment line item {} for Application Fee and handing over to payment gateway".format(
                        f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                        proposal.id,
                    )
                )
                return checkout_response

        except Exception as e:
            logger.error(f"Error Creating Application Fee: {e}")
            if application_fee:
                application_fee.delete()
            raise


class ComplianceFeeView(TemplateView):
    template_name = "commercialoperator/booking/success.html"

    def get_object(self):
        return get_object_or_404(Compliance, id=self.kwargs["compliance_pk"])

    def post(self, request, *args, **kwargs):

        compliance = self.get_object()

        user = request.user
        try:
            user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            if not (
                is_internal(self.request)
                or compliance.proposal.org_applicant in user_orgs
                or compliance.proposal.submitter == user
            ):
                raise PermissionDenied
        except:
            raise

        compliance_fee = ComplianceFee.objects.create(
            compliance=compliance,
            created_by=request.user,
            payment_type=ComplianceFee.PAYMENT_TYPE_TEMPORARY,
        )

        # NOTE: files have to be uploaded prior to payment
        # TODO: file upload does not appear to work - investigate (here and in the standard submit)
        # TODO: consider file upload as a separate process to submission so users don't have to upload every submit attempt
        if request.FILES:
            for f in request.FILES:
                document = compliance.documents.create(name=str(request.FILES[f]))
                document._file = request.FILES[f]
                document.save()

        try:
            with transaction.atomic():
                set_session_compliance_invoice(request.session, compliance_fee)
                lines = create_compliance_fee_lines(compliance)
                return_url = request.build_absolute_uri(
                    reverse(
                        "compliance_fee_success",
                        kwargs={"reference": compliance.lodgement_number},
                    )
                )
                return_preload_url = settings.COMMERCIALOPERATOR_EXTERNAL_URL + reverse(
                    "compliance_success_preload",
                    kwargs={"reference": compliance.lodgement_number},
                )
                checkout_response = checkout(
                    request,
                    compliance.proposal,
                    lines,
                    return_url,
                    return_preload_url,
                    invoice_text="Per participant licence charge",
                    reference=compliance.lodgement_number,
                )

                # Set session variables
                # TODO rework to use its own model (if necessary)
                request.session["payment_pk"] = compliance.proposal.pk
                request.session["payment_model"] = "proposal"

                logger.info(
                    "{} built payment line item {} for Compliance Fee and handing over to payment gateway".format(
                        f"User {compliance.proposal.submitter.get_full_name()} with id {compliance.proposal.submitter.id}",
                        compliance.id,
                    )
                )
                return checkout_response

        except Exception as e:
            logger.error(f"Error Creating Compliance Fee: {e}")
            if compliance_fee:
                compliance_fee.delete()
            raise


class FilmingFeeView(TemplateView):
    template_name = "commercialoperator/booking/success.html"

    def get_object(self):
        return get_object_or_404(Proposal, id=self.kwargs["proposal_pk"])

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        proposal = self.get_object()

        user = request.user
        try:
            user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
            ):
                raise PermissionDenied
        except:
            raise

        filming_fee = proposal.filming_fees.order_by("-id").first()
        inv_ref = (
            filming_fee.filming_fee_invoices.order_by("-id").first().invoice_reference
        )

        try:
            set_session_filming_invoice(request.session, filming_fee)
            invoice = Invoice.objects.get(reference=inv_ref)

            checkout_response = checkout_existing_invoice(
                request,
                proposal.lodgement_number,
                invoice,
                return_url_ns="filming_fee_success",
            )

            logger.info(
                "{} built payment line item {} for Proposal Fee and handing over to payment gateway".format(
                    f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                    proposal.id,
                )
            )

            # Set session variables
            request.session["payment_pk"] = proposal.pk
            request.session["payment_model"] = "proposal"

            return checkout_response

        except Exception as e:
            logger.error(f"Error Creating Proposal Fee: {e}")
            if filming_fee:
                filming_fee.delete()
            raise


# TODO (may not be needed, in which case remove)
class DeferredInvoicingPreviewView(TemplateView):
    template_name = "commercialoperator/booking/preview_deferred.html"

    def post(self, request, *args, **kwargs):

        payment_method = self.request.GET.get("method")
        context = template_context(self.request)
        proposal_id = int(kwargs["proposal_pk"])
        proposal = Proposal.objects.get(id=proposal_id)

        user = request.user
        try:
            user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
            ):
                raise PermissionDenied
        except:
            raise

        try:
            submitter = proposal.applicant
        except:
            submitter = proposal.submitter

        if isinstance(proposal.org_applicant, Organisation) and (
            proposal.org_applicant.monthly_invoicing_allowed
            or proposal.org_applicant.bpay_allowed
            or (settings.OTHER_PAYMENT_ALLOWED and is_payment_admin(request.user))
        ):
            try:
                lines = create_lines(request)
                logger.info(
                    "{} Show Park Bookings Preview for BPAY/Other/monthly invoicing".format(
                        f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                    )
                )
                context.update(
                    {
                        "lines": lines,
                        "line_details": request.POST["payment"],
                        "proposal_id": proposal_id,
                        "submitter": submitter,
                        "payment_method": payment_method,
                    }
                )
                return render(request, self.template_name, context)

            except Exception as e:
                logger.error(f"Error creating booking preview: {e}")
        else:
            logger.error(f"Error creating booking preview: {e}")
            raise


# TODO replace below with appropriate payment functionality (may not be needed, in which case remove)
class DeferredInvoicingView(TemplateView):
    template_name = "commercialoperator/booking/success.html"

    def post(self, request, *args, **kwargs):

        payment_method = self.request.POST.get("method")
        context = template_context(self.request)
        proposal_id = int(kwargs["proposal_pk"])
        proposal = Proposal.objects.get(id=proposal_id)

        user = request.user
        try:
            user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
            ):
                raise PermissionDenied
        except:
            raise

        try:
            submitter = proposal.applicant
        except:
            submitter = proposal.submitter

        if isinstance(proposal.org_applicant, Organisation):
            try:
                if proposal.org_applicant.bpay_allowed and payment_method == "bpay":
                    booking_type = Booking.BOOKING_TYPE_INTERNET
                elif (
                    proposal.org_applicant.monthly_invoicing_allowed
                    and payment_method == "monthly_invoicing"
                ):
                    booking_type = Booking.BOOKING_TYPE_MONTHLY_INVOICING
                else:
                    booking_type = Booking.BOOKING_TYPE_RECEPTION

                booking = create_booking(request, proposal, booking_type=booking_type)
                invoice_reference = None
                if booking and payment_method == "bpay":
                    # BPAY/OTHER invoice are created immediately. Monthly invoices are created later by Cron
                    ret = create_bpay_invoice(submitter, booking)
                    invoice_reference = booking.invoice.reference

                if booking and payment_method == "other":
                    # BPAY/Other invoice are created immediately. Monthly invoices are created later by Cron
                    ret = create_other_invoice(submitter, booking)
                    invoice_reference = booking.invoice.reference

                if booking and payment_method == "monthly_invoicing":
                    # For monthly_invoicing, invoice is created later by Cron. Now we only create a confirmation
                    ret = create_monthly_confirmation(submitter, booking)

                logger.info(
                    "{} Created Park Bookings with payment method {} for Proposal ID {}".format(
                        f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                        payment_method,
                        proposal.id,
                    )
                )
                # send_monthly_invoicing_confirmation_tclass_email_notification(request, booking, invoice, recipients=[recipient])
                context.update(
                    {
                        "booking": booking,
                        "booking_id": booking.id,
                        "submitter": submitter,
                        "monthly_invoicing": (
                            True if payment_method == "monthly_invoicing" else False
                        ),
                        "invoice_reference": invoice_reference,
                    }
                )
                if payment_method == "other":
                    if is_payment_admin(request.user):
                        return HttpResponseRedirect(
                            reverse("payments:invoice-payment")
                            + f"?invoice={invoice_reference}"
                        )
                    else:
                        raise PermissionDenied
                else:
                    return render(request, self.template_name, context)

            except Exception as e:
                logger.error(f"Error Creating booking: {e}")
                if booking:
                    booking.delete()
                raise
        else:
            logger.error(f"Error Creating booking: {e}")
            raise


# TODO: determine if non-cc payments are still required - handle as needed with alternative payment approaches (if required)
class MakePaymentView(TemplateView):
    """View to handle Park Entry Fees:Make Payment"""

    template_name = "commercialoperator/booking/success.html"

    def post(self, request, *args, **kwargs):

        proposal_id = int(kwargs["proposal_pk"])
        proposal = Proposal.objects.get(id=proposal_id)

        user = request.user
        try:
            user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
            ):
                raise PermissionDenied
        except:
            raise

        booking = None

        try:
            booking = create_booking(
                request, proposal, booking_type=Booking.BOOKING_TYPE_TEMPORARY
            )

            # check for duplicate bookings/lines
            unique_lines = [
                dict(s)
                for s in set(frozenset(d.items()) for d in booking.as_line_items)
            ]
            if len(booking.as_line_items) != len(unique_lines):
                logger.warning("Booking contains dupicate rows.")

            with transaction.atomic():
                set_session_booking(request.session, booking)
                return_url = request.build_absolute_uri(
                    reverse(
                        "public_booking_success",
                        kwargs={"reference": proposal.lodgement_number},
                    )
                )
                return_preload_url = settings.COMMERCIALOPERATOR_EXTERNAL_URL + reverse(
                    "public_booking_success_preload",
                    kwargs={"reference": proposal.lodgement_number},
                )
                checkout_response = checkout(
                    request,
                    proposal,
                    booking.as_line_items,
                    return_url,
                    return_preload_url,
                    invoice_text="Payment Invoice",
                    reference=proposal.lodgement_number,
                )

                # Set session variables
                # TODO use booking pk and model instead
                request.session["payment_pk"] = proposal.pk
                request.session["payment_model"] = "proposal"

                logger.info(
                    "{} built payment line items {} for Park Bookings and handing over to payment gateway".format(
                        f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                        proposal.id,
                    )
                )
                return checkout_response

        except Exception as e:
            logger.error(f"Error Creating booking: {e}")
            raise


class ComplianceFeeSuccessViewPreload(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference, format=None):
        print("ComplianceFeeSuccessViewPreload")

        invoice_ref = request.GET.get("invoice")

        try:
            compliance = Compliance.objects.get(lodgement_number=reference)
            print("compliance:", compliance)
        except Exception as e:
            print(e)
            return redirect("home")

        # use the latest Fee record
        compliance_fee = (
            ComplianceFee.objects.filter(compliance=compliance)
            .order_by("created")
            .last()
        )

        booking_reference = compliance.lodgement_number
        if not validate_booking_and_invoice_references(booking_reference, invoice_ref):
            raise serializers.ValidationError(f"Invoice: {invoice_ref} and Booking Reference: {booking_reference} are not part of the same order/basket.")

        _, _ = ComplianceFeeInvoice.objects.get_or_create(
            compliance_fee=compliance_fee, invoice_reference=invoice_ref
        )

        if compliance_fee.payment_type == ComplianceFee.PAYMENT_TYPE_TEMPORARY:
            compliance_fee.payment_type = ComplianceFee.PAYMENT_TYPE_INTERNET
            compliance_fee.expiry_time = None
            success = False
            try:
                inv = Invoice.objects.get(reference=invoice_ref)
                invoice_properties = get_invoice_properties(inv.id)
                payment_status = invoice_properties.get("invoice", {}).get(
                    "payment_status"
                )

                if payment_status == "paid" or payment_status == "over_paid":
                    compliance.submit()
                    compliance.fee_invoice_reference = invoice_ref
                    compliance.save()
                    success = False
                else:
                    logger.error(f"Invoice payment status is {payment_status}")
                    raise serializers.ValidationError(
                        f"Invoice payment status is {payment_status}"
                    )

            except Exception as e:
                print(e)
                raise serializers.ValidationError("Fee success preload failed")

            if success:
                compliance_fee.save()
                try:
                    send_compliance_fee_invoice_events_email_notification(  # TODO fix this
                        request,
                        compliance,
                        inv,
                        recipients=[compliance.proposal.submitter.email],
                    )
                except Exception:
                    # log the error but do not invalidate the payment and subsequent compliance submission
                    logger.exception(
                        "Unable to send compliance fee invoice email notification"
                    )

        return Response(status=status.HTTP_200_OK)


class ComplianceFeeSuccessView(TemplateView):
    template_name = "commercialoperator/booking/success_compliance_fee.html"

    def valid_token_payment_session(self, request, invoice_reference):
        if 'token_payment_session' in request.session:
            basket = Basket.objects.filter(status='Submitted', id=request.session['token_payment_session']).order_by('-id').first()
            del request.session['token_payment_session']
            return validate_booking_and_invoice_references(basket.booking_reference, invoice_reference)

    def get(self, request, *args, **kwargs):
        print("ComplianceFeeSuccessView")
        lodgement_number = kwargs.get("reference")

        try:
            compliance = Compliance.objects.get(lodgement_number=lodgement_number)
        except:
            raise serializers.ValidationError("Compliance does not exist")

        if 'token_payment_session' in request.session:
            invoice_ref = request.GET.get("invoice", "")
        else:
            compliance_fee = get_session_compliance_invoice(request.session)
            fee_inv = compliance_fee.compliance_fee_invoices.order_by("-id").first()
            invoice_ref = fee_inv.invoice_reference

        user = request.user
        try:
            try:
                user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            except:
                user_orgs = []
            if not (
                is_internal(self.request)
                or compliance.proposal.org_applicant in user_orgs
                or compliance.proposal.submitter == user
                or self.valid_token_payment_session(request, invoice_ref)
            ):
                raise PermissionDenied
        except:
            raise

        try:
            inv = Invoice.objects.get(reference=invoice_ref)
        except:
            inv = None

        context = {
            "proposal": compliance.proposal,
            "submitter": compliance.submitter,
            "fee_invoice": inv,
        }
        return render(request, self.template_name, context)


class FilmingFeeSuccessViewPreload(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference, format=None):
        print("FilmFeeSuccessViewPreload")

        invoice_ref = request.GET.get("invoice")

        try:
            proposal = Proposal.objects.get(lodgement_number=reference)
            print("proposal:", proposal)
        except Exception as e:
            print(e)
            return redirect("home")

        try:
            filming_fee = (
                FilmingFeeInvoice.objects.filter(invoice_reference=invoice_ref)
                .last()
                .filming_fee
            )
        except:
            raise serializers.ValidationError("Filming Fee not found")

        if filming_fee.proposal != proposal:
            raise serializers.ValidationError(
                "Filming Fee Proposal does not match provided lodgement number"
            )

        booking_reference = proposal.lodgement_number
        if not validate_booking_and_invoice_references(booking_reference, invoice_ref):
            raise serializers.ValidationError(f"Invoice: {invoice_ref} and Booking Reference: {booking_reference} are not part of the same order/basket.")

        if filming_fee.payment_type == FilmingFee.PAYMENT_TYPE_TEMPORARY:
            filming_fee.payment_type = ApplicationFee.PAYMENT_TYPE_INTERNET
            filming_fee.expiry_time = None
            success = False
            try:
                inv = Invoice.objects.get(reference=invoice_ref)
                invoice_properties = get_invoice_properties(inv.id)
                payment_status = invoice_properties.get("invoice", {}).get(
                    "payment_status"
                )
                if proposal and payment_status in ["paid", "over_paid"]:
                    proposal.fee_invoice_reference = invoice_ref
                    proposal.save()
                    proposal.final_approval()
                    proposal.reset_application_discount(
                        proposal.submitter
                    )  # TODO verify using submitter is ok
                else:
                    logger.error(f"Invoice payment status is {inv.payment_status}")
                    raise serializers.ValidationError(
                        f"Invoice payment status is {inv.payment_status}"
                    )
            except Exception as e:
                print(e)
                raise serializers.ValidationError("Fee success preload failed")

            if success:
                filming_fee.save()

        return Response(status=status.HTTP_200_OK)


class FilmingFeeSuccessView(TemplateView):
    template_name = "commercialoperator/booking/success_fee.html"

    def valid_token_payment_session(self, request, invoice_reference):
        if 'token_payment_session' in request.session:
            basket = Basket.objects.filter(status='Submitted', id=request.session['token_payment_session']).order_by('-id').first()
            del request.session['token_payment_session']
            return validate_booking_and_invoice_references(basket.booking_reference, invoice_reference)

    def get(self, request, *args, **kwargs):
        print("FilmingFeeSuccessView")
        lodgement_number = kwargs.get("reference")

        try:
            proposal = Proposal.objects.get(lodgement_number=lodgement_number)
        except:
            raise serializers.ValidationError("Proposal does not exist")

        if 'token_payment_session' in request.session:
            invoice_ref = request.GET.get("invoice", "")
        else:
            filming_fee = get_session_filming_invoice(request.session)
            fee_inv = filming_fee.filming_fee_invoices.order_by("-id").first()
            invoice_ref = fee_inv.invoice_reference

        user = request.user
        try:
            try:
                user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            except:
                user_orgs = []
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
                or self.valid_token_payment_session(request, invoice_ref)
            ):
                raise PermissionDenied
        except:
            raise

        applicant = proposal.applicant_obj
        try:
            if applicant.email:
                submitter = applicant.email
            else:
                submitter = (
                    proposal.submitter.email
                    if proposal and proposal.submitter
                    else None
                )
        except:
            submitter = (
                proposal.submitter.email if proposal and proposal.submitter else None
            )

        try:
            inv = Invoice.objects.get(reference=invoice_ref)
        except:
            inv = None

        context = {"proposal": proposal, "submitter": submitter, "fee_invoice": inv}
        return render(request, self.template_name, context)


class ApplicationFeeSuccessViewPreload(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference, format=None):
        print("ApplicationFeeSuccessViewPreload")

        invoice_ref = request.GET.get("invoice")

        try:
            proposal = Proposal.objects.get(lodgement_number=reference)
            print("proposal:", proposal)
        except Exception as e:
            print(e)
            return redirect("home")

        # use the latest Fee record
        proposal_fee = (
            ApplicationFee.objects.filter(proposal=proposal).order_by("created").last()
        )

        booking_reference = proposal.lodgement_number
        if not validate_booking_and_invoice_references(booking_reference, invoice_ref):
            raise serializers.ValidationError(f"Invoice: {invoice_ref} and Booking Reference: {booking_reference} are not part of the same order/basket.")

        _, _ = ApplicationFeeInvoice.objects.get_or_create(
            application_fee=proposal_fee, invoice_reference=invoice_ref
        )

        if proposal_fee.payment_type == ApplicationFee.PAYMENT_TYPE_TEMPORARY:
            proposal_fee.payment_type = ApplicationFee.PAYMENT_TYPE_INTERNET
            proposal_fee.expiry_time = None
            success = False
            try:
                inv = Invoice.objects.get(reference=invoice_ref)
                invoice_properties = get_invoice_properties(inv.id)
                payment_status = invoice_properties.get("invoice", {}).get(
                    "payment_status"
                )

                if payment_status == "paid" or payment_status == "over_paid":
                    proposal = proposal_submit(proposal)
                    proposal.fee_invoice_reference = invoice_ref
                    proposal.save()
                    proposal.reset_application_discount(proposal.submitter)
                    success = True
                else:
                    logger.error(f"Invoice payment status is {payment_status}")
                    raise serializers.ValidationError(
                        f"Invoice payment status is {payment_status}"
                    )

            except Exception as e:
                print(e)
                raise serializers.ValidationError("Fee success preload failed")

            if success:
                proposal_fee.save()
                applicant = proposal.applicant_obj
                try:
                    recipient = Organisation.objects.get(id=applicant.id).email
                except:
                    recipient = proposal.submitter.email

                try:
                    # NOTE: request=None works fine with this email function
                    send_application_fee_invoice_tclass_email_notification(
                        request, proposal, inv, recipients=[recipient]
                    )
                except Exception:
                    # log the error but do not invalidate the payment and subsequent compliance submission
                    logger.error(
                        "Unable to send compliance fee invoice email notification"
                    )

        return Response(status=status.HTTP_200_OK)


class ApplicationFeeSuccessView(TemplateView):
    template_name = "commercialoperator/booking/success_fee.html"

    def valid_token_payment_session(self, request, invoice_reference):
        if 'token_payment_session' in request.session:
            basket = Basket.objects.filter(status='Submitted', id=request.session['token_payment_session']).order_by('-id').first()
            del request.session['token_payment_session']
            return validate_booking_and_invoice_references(basket.booking_reference, invoice_reference)

    def get(self, request, *args, **kwargs):
        print("ApplicationFeeSuccessView")
        lodgement_number = kwargs.get("reference")

        try:
            proposal = Proposal.objects.get(lodgement_number=lodgement_number)
        except:
            raise serializers.ValidationError("Proposal does not exist")

        if 'token_payment_session' in request.session:
            invoice_ref = request.GET.get("invoice", "")
        else:
            application_fee = get_session_application_invoice(request.session)
            fee_inv = application_fee.application_fee_invoices.order_by("-id").first()
            invoice_ref = fee_inv.invoice_reference

        user = request.user
        try:
            try:
                user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            except:
                user_orgs = []
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
                or self.valid_token_payment_session(request, invoice_ref)
            ):
                raise PermissionDenied
        except:
            raise

        applicant = proposal.applicant_obj
        try:
            if applicant.email:
                submitter = applicant.email
            else:
                submitter = (
                    proposal.submitter.email
                    if proposal and proposal.submitter
                    else None
                )
        except:
            submitter = (
                proposal.submitter.email if proposal and proposal.submitter else None
            )

        try:
            inv = Invoice.objects.get(reference=invoice_ref)
        except:
            inv = None

        context = {"proposal": proposal, "submitter": submitter, "fee_invoice": inv}
        return render(request, self.template_name, context)


class BookingSuccessViewPreload(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference, format=None):
        print("BookingSuccessViewPreload")

        invoice_ref = request.GET.get("invoice")

        try:
            proposal = Proposal.objects.get(lodgement_number=reference)
            print("proposal:", proposal)
        except Exception as e:
            print(e)
            return redirect("home")

        # use the latest Fee record
        booking = Booking.objects.filter(proposal=proposal).order_by("created").last()

        booking_reference = proposal.lodgement_number
        if not validate_booking_and_invoice_references(booking_reference, invoice_ref):
            raise serializers.ValidationError(f"Invoice: {invoice_ref} and Booking Reference: {booking_reference} are not part of the same order/basket.")

        _, created = BookingInvoice.objects.get_or_create(
            booking=booking,
            invoice_reference=invoice_ref,
            payment_method=Invoice.PAYMENT_METHOD_CC,  # if we are here, it was paid by credit_card
        )

        if created:
            try:
                logger.info(
                    "{} Created Park Bookings Invoice {} for Booking ID {}".format(
                        f"User {proposal.submitter.get_full_name()} with id {proposal.submitter.id}",
                        invoice_ref,
                        booking.id,
                    )
                )
            except:
                logger.error("Unable to log booking invoice creation")

        if booking.booking_type == Booking.BOOKING_TYPE_TEMPORARY:
            booking.booking_type = Booking.BOOKING_TYPE_INTERNET
            booking.expiry_time = None
            success = False
            try:
                inv = Invoice.objects.get(reference=invoice_ref)
                invoice_properties = get_invoice_properties(inv.id)
                payment_status = invoice_properties.get("invoice", {}).get(
                    "payment_status"
                )

                if payment_status == "paid" or payment_status == "over_paid":
                    success = True
                else:
                    logger.error(f"Invoice payment status is {payment_status}")
                    raise serializers.ValidationError(
                        f"Invoice payment status is {payment_status}"
                    )

            except Exception as e:
                print(e)
                raise serializers.ValidationError("Fee success preload failed")

            if success:
                booking.save()
                recipients = []

                try:
                    recipients.append(proposal.applicant.email)
                except:
                    if proposal.submitter and proposal.submitter.email:
                        recipients.append(proposal.submitter.email)

                if recipients:
                    # TODO using submitter instead of request user as sender but ideally sender should be the system in all cases (tbd)
                    send_invoice_tclass_email_notification(
                        proposal.submitter, booking, inv, recipients=recipients
                    )
                    send_confirmation_tclass_email_notification(
                        proposal.submitter, booking, inv, recipients=recipients
                    )

        return Response(status=status.HTTP_200_OK)


class BookingSuccessView(TemplateView):
    template_name = "commercialoperator/booking/success.html"

    def valid_token_payment_session(self, request, invoice_reference):
        if 'token_payment_session' in request.session:
            basket = Basket.objects.filter(status='Submitted', id=request.session['token_payment_session']).order_by('-id').first()
            del request.session['token_payment_session']
            return validate_booking_and_invoice_references(basket.booking_reference, invoice_reference)

    def get(self, request, *args, **kwargs):
        print("BookingSuccessView")
        lodgement_number = kwargs.get("reference")

        try:
            proposal = Proposal.objects.get(lodgement_number=lodgement_number)
        except:
            raise serializers.ValidationError("Proposal does not exist")

        booking = Booking.objects.filter(proposal=proposal).order_by("created").last()
        fee_inv = booking.invoices.order_by("-id").first()

        if 'token_payment_session' in request.session:
            invoice_ref = request.GET.get("invoice", "")
            if invoice_ref != fee_inv.invoice_reference:
                logger.warning("Latest booking record invoice and invoice in request do not match")
        else:
            session_booking = get_session_booking(request.session)
            invoice_ref = fee_inv.invoice_reference
            if booking != session_booking:
                logger.warning("Latest booking record and booking in session do not match")

        user = request.user
        try:
            try:
                user_orgs = [org.id for org in user.commercialoperator_organisations.all()]
            except:
                user_orgs = []
            if not (
                is_internal(self.request)
                or proposal.org_applicant in user_orgs
                or proposal.submitter == user
                or self.valid_token_payment_session(request, invoice_ref)
            ):
                raise PermissionDenied
        except:
            raise

        applicant = proposal.applicant_obj
        try:
            if applicant.email:
                submitter = applicant.email
            else:
                submitter = (
                    proposal.submitter.email
                    if proposal and proposal.submitter
                    else None
                )
        except:
            submitter = (
                proposal.submitter.email if proposal and proposal.submitter else None
            )

        try:
            inv = Invoice.objects.get(reference=invoice_ref)
        except:
            inv = None

        context = {
            "booking_id": booking.id,
            "submitter": submitter,
            "payer": request.user,
            "invoice_reference": inv.reference if inv else None,
        }
        return render(request, self.template_name, context)


class InvoicePDFView(View):
    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])
        bi = BookingInvoice.objects.filter(invoice_reference=invoice.reference).last()

        if bi:
            proposal = bi.booking.proposal
        else:
            proposal = Proposal.objects.get(fee_invoice_reference=invoice.reference)

        organisation = proposal.org_applicant

        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")

            invoice_pdf = get_invoice_pdf(invoice.reference)

            if invoice_pdf.status_code == status.HTTP_200_OK or is_payment_admin(
                request.user
            ):
                response.write(invoice_pdf.content)
                return response

        raise PermissionDenied

    def get_object(self):
        return get_object_or_404(Invoice, reference=self.kwargs["reference"])

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class InvoiceFilmingFeePDFView(View):
    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])
        proposal = Proposal.objects.get(fee_invoice_reference=invoice.reference)

        organisation = proposal.org_applicant
        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")
            invoice_pdf = get_invoice_pdf(invoice.reference)

            if invoice_pdf.status_code == status.HTTP_200_OK:
                response.write(invoice_pdf.content)
                return response
            else:
                logger.error(
                    f"Error getting PDF for invoice {invoice.reference}: {invoice_pdf.reason}"
                )

        raise PermissionDenied

    def get_object(self):
        return get_object_or_404(Invoice, reference=self.kwargs["reference"])

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class InvoiceCompliancePDFView(View):
    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])
        cfi = ComplianceFeeInvoice.objects.filter(
            invoice_reference=invoice.reference
        ).last()

        compliance = cfi.compliance_fee.compliance

        organisation = (
            compliance.proposal.org_applicant if compliance.proposal else None
        )
        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")

            invoice_pdf = get_invoice_pdf(invoice.reference)
            if invoice_pdf.status_code == status.HTTP_200_OK:
                response.write(invoice_pdf.content)
                return response
            else:
                logger.error(
                    f"Error getting PDF for invoice {invoice.reference}: {invoice_pdf.reason}"
                )
            return response
        raise PermissionDenied

    def get_object(self):
        return get_object_or_404(Invoice, reference=self.kwargs["reference"])

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class ConfirmationPDFView(View):
    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])
        bi = BookingInvoice.objects.filter(invoice_reference=invoice.reference).last()
        organisation = bi.booking.proposal.org_applicant

        if self.check_owner(organisation):
            # GST ignored here because GST amount is not included on the confirmation PDF
            response = HttpResponse(content_type="application/pdf")
            response.write(
                create_confirmation_pdf_bytes("confirmation.pdf", invoice, bi.booking)
            )
            return response
        raise PermissionDenied

    def get_object(self):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])
        return invoice

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class MonthlyConfirmationPDFBookingView(View):
    """for the Visitor Admissions Payment Dashboard - View by Booking (payments_dashboard.vue)"""

    def get(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs["id"])
        organisation = booking.proposal.org_applicant

        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")
            response.write(
                create_monthly_confirmation_pdf_bytes(
                    "monthly_confirmation.pdf", booking
                )
            )
            return response
        raise PermissionDenied

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class MonthlyConfirmationPDFParkBookingView(View):
    """for the Visitor Admissions Payment Dashboard - View by ParkBooking (parkbookings_dashboard.vue)"""

    def get(self, request, *args, **kwargs):
        park_booking = get_object_or_404(ParkBooking, id=self.kwargs["id"])
        booking = park_booking.booking
        organisation = (
            booking.proposal.org_applicant.organisation.organisation_set.all()[0]
        )

        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")
            response.write(
                create_monthly_confirmation_pdf_bytes(
                    "monthly_confirmation.pdf", booking
                )
            )
            return response
        raise PermissionDenied

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class AwaitingPaymentInvoicePDFView(View):
    def get(self, request, *args, **kwargs):
        proposal = get_object_or_404(Proposal, id=self.kwargs["id"])
        organisation = proposal.org_applicant

        if self.check_owner(organisation):
            response = HttpResponse(content_type="application/pdf")

            if proposal.application_type.name == ApplicationType.FILMING:
                invoice = Invoice.objects.get(
                    reference=proposal.filming_fee_invoice_reference
                )
            else:
                invoice = proposal.invoice

            if not invoice:
                raise Http404("Invoice not found")

            invoice_pdf = get_invoice_pdf(invoice.reference)

            if invoice_pdf.status_code == status.HTTP_200_OK:
                response.write(invoice_pdf.content)
                return response

        raise PermissionDenied

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class InvoicePaymentView(View):
    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs["reference"])

        if is_payment_admin(request.user):
            ledger_invoice_url = urljoin(
                settings.LEDGER_UI_URL,
                f"ledger/payments/oracle/payments?invoice_no={invoice.reference}",
            )
            return HttpResponseRedirect(ledger_invoice_url)

        raise PermissionDenied

    def get_object(self):
        return get_object_or_404(Invoice, reference=self.kwargs["reference"])

    def check_owner(self, organisation):
        return (
            is_in_organisation_contacts(self.request, organisation)
            or is_internal(self.request)
            or self.request.user.is_superuser
        )


class SessionAbortRedirectView(TemplateView):
    template_name = "commercialoperator/booking/abort_session.html"

    def get(self, request, *args, **kwargs):
        booking = None
        context = None
        action = request.GET.get("action", None)

        try:
            booking = get_session_booking(request.session)

            # only ever delete a booking object if it's marked as temporary
            if booking.booking_type == 3:
                booking.delete()
            delete_session_booking(request.session)

        except Exception as e:
            logger.warning(f"Error deleting session booking: {e}")
        else:
            pass

        if action == "quit":
            # if the user wants to quit, we redirect to the home page
            return HttpResponseRedirect(reverse("home"))

        context = template_context(self.request)
        return render(request, self.template_name, context)
