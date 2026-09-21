import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone as dj_timezone

import pyotp

from accounts.tests.factories import PASSWORD
from audit.models import SecurityEvent
from mfa.models import MFADevice
from mfa.services.crypto import encrypt_secret
from research.scenarios import SCENARIOS

RESULTS_DIR = Path(settings.BASE_DIR) / "research" / "results"


class Command(BaseCommand):
    help = "Ekzekuton skenarët eksperimentalë A-H kundër aplikacionit lokal."

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true", help="Mos i fshi llogaritë e testit.")

    def handle(self, *args, **options):
        if not getattr(settings, "RESEARCH_MODE", False):
            raise CommandError(
                "RESEARCH_MODE nuk është aktiv. Përdor --settings=config.settings.research"
            )

        run_id = uuid.uuid4().hex[:12]
        started = dj_timezone.now()
        User = get_user_model()

        self.stdout.write(f"Run ID: {run_id}")
        self.stdout.write("Pastrim i llogarive të mëparshme të eksperimentit...")
        self._cleanup(User)

        created = []

        def user_factory(username, with_mfa=False):
            user = User.objects.create_user(
                username=username,
                email=f"{username}@research.local",
                password=PASSWORD,
            )
            created.append(user)
            if with_mfa:
                secret = pyotp.random_base32()
                MFADevice.objects.create(
                    user=user,
                    secret_encrypted=encrypt_secret(secret),
                    is_confirmed=True,
                    confirmed_at=dj_timezone.now(),
                )
                return user, secret
            return user

        results = []
        for key, (title, func) in SCENARIOS.items():
            self.stdout.write(f"  Scenario {key}: {title} ...")
            outcome = func(user_factory)
            outcome["scenario"] = key
            outcome["title"] = title
            results.append(outcome)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = started.strftime("%Y%m%d_%H%M%S")

        json_path = RESULTS_DIR / f"experiment_{stamp}_{run_id}.json"
        json_path.write_text(
            json.dumps(
                {"run_id": run_id, "started": started.isoformat(), "results": results},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        csv_path = RESULTS_DIR / f"experiment_{stamp}_{run_id}.csv"
        self._write_csv(csv_path, results)

        if not options["keep"]:
            self._cleanup(User)
            self.stdout.write("Llogaritë e testit u fshinë.")
        else:
            self.stdout.write("Llogaritë e testit u ruajtën (--keep).")

        self.stdout.write(self.style.SUCCESS(f"\nPërfundoi. Rezultatet:\n  {csv_path}\n  {json_path}"))

    def _cleanup(self, User):
        with transaction.atomic():
            User.objects.filter(username__startswith="exp_").delete()

    def _write_csv(self, path, results):
        fields = sorted({key for row in results for key in row})
        ordered = ["scenario", "title"] + [f for f in fields if f not in ("scenario", "title")]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ordered)
            writer.writeheader()
            for row in results:
                writer.writerow(row)