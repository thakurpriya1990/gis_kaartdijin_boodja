from django.core.management.base import BaseCommand
from django.contrib import auth
from django.conf import settings
from datetime import datetime
import requests
import json
import codecs
import decouple
import logging
from govapp.apps.accounts import utils, emails


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Ref: https://github.com/dbca-wa/ledger/blob/master/ledger/accounts/management/commands/sync_itassets_users.py
    """
    help = 'Sync Itassets Users.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        try:
            logger.info("Syncing Itassets Users ...")
            ITASSETS_USER_JSON_URL = decouple.config('ITASSETS_USER_JSON_URL', default=[])
            ITASSETS_USER_LOGIN = decouple.config('ITASSETS_USER_LOGIN', default='')
            ITASSETS_USER_TOKEN = decouple.config('ITASSETS_USER_TOKEN', default='')
            url = ITASSETS_USER_JSON_URL
            resp = requests.get(url, data ={}, auth=(ITASSETS_USER_LOGIN, ITASSETS_USER_TOKEN))
            data = json.loads(codecs.decode(resp.text.encode(), 'utf-8-sig'))
            row = 0
            noaccount = 0
            updatedaccount = 0
            for user in data:
                ed = str(user["email"]).split("@")
                email_domain = ed[1]
                if email_domain in settings.DEPT_DOMAINS:
                    email = user['email'].lower()
                    first_name = user['given_name']
                    last_name = user['surname']
                    if first_name is None or first_name == '':
                        first_name = "No First Name"
                    if last_name is None or last_name == '':
                        last_name = "No Last Name"

                    UserModel = auth.get_user_model()
                    user_objects = UserModel.objects.filter(email=email)
                    if user_objects.count() > 0:
                        existing_user = user_objects[0]
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        existing_user.is_staff = True
                        existing_user.save()
                        logger.info(f"User: [{existing_user}] has been updated.")
                        updatedaccount = updatedaccount + 1
                    else:
                        new_user = UserModel.objects.create_user(
                            username=email,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            is_staff=True,
                        )
                        logger.info(f"User: [{new_user}] has been created.")
                        noaccount = noaccount + 1
                    row = row + 1

            logger.info(f"Successfully Completed Itassets Users Import.  Created Users: {str(noaccount)}.  Updated Users: {str(updatedaccount)}")
        except Exception as e:
            time_error = str(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            logger.error(f"Itassets Users Sync Error: {e}")
            emails.SyncItassetsUsersEmail().send_to(
                *utils.all_administrators(),  # All administrators
                context = {
                    "ad_error": e,
                    "time_error": time_error,
                },
            )
