import hashlib
from django.conf import settings
from ledger_api_client import utils as ledger_api_utils
from commercialoperator.helpers import is_commercialoperator_admin

from commercialoperator.components.organisations.models import Organisation
from commercialoperator.settings import (
    TEMPLATE_GROUP,
    TEMPLATE_HEADER_LOGO,
    TEMPLATE_TITLE,
    VUE3_ENTRY_SCRIPT,
)


def commercialoperator_url(request):

    checkouthash = None
    if "payment_model" in request.session and "payment_pk" in request.session:
        checkouthash = hashlib.sha256(
            str(
                str(request.session["payment_model"])
                + str(request.session["payment_pk"])
            ).encode("utf-8")
        ).hexdigest()
        #check for ledger-api-client set checkouthash - if it is remove payment_model and payment_pk session variables and replace checkouthash
        if 'token_payment_session' in request.session:
            del request.session['payment_model']
            del request.session['payment_pk']

    if 'token_payment_session' in request.session:
        checkouthash =  hashlib.sha256(str(request.session["token_payment_session"]).encode('utf-8')).hexdigest()

    organisations_user_can_admin = Organisation.organisations_user_can_admin(
        request.user.id
    )
    ledger_totals = ledger_api_utils.get_ledger_totals()
    return {
        "template_group": TEMPLATE_GROUP,
        "template_header_logo": TEMPLATE_HEADER_LOGO,
        "template_title": TEMPLATE_TITLE,
        "organisations_user_can_admin": organisations_user_can_admin,
        "build_tag": settings.BUILD_TAG,
        "LEDGER_UI_URL": settings.LEDGER_UI_URL,
        "PAYMENT_SYSTEM_PREFIX": settings.PAYMENT_SYSTEM_PREFIX,
        "ledger_totals": ledger_totals,
        "checkouthash": checkouthash,
        "vue3_entry_script": VUE3_ENTRY_SCRIPT,
        "is_commercialoperator_admin": is_commercialoperator_admin(request),
   }
