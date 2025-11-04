from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.company.models import Company


class Command(BaseCommand):
    help = _(
        "Safely reset DF-e NSU (set last_nsu=0) for a company, respecting SEFAZ cooldown window."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            dest="company_id",
            help=_("Company UUID (primary key)."),
        )
        parser.add_argument(
            "--cnpj",
            dest="cnpj",
            help=_("Company CNPJ (digits only or formatted)."),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help=_("Force reset even within cooldown window (not recommended)."),
        )

    def handle(self, *args, **options):
        company_id: Optional[str] = options.get("company_id")
        cnpj: Optional[str] = options.get("cnpj")
        force: bool = bool(options.get("force"))

        if not company_id and not cnpj:
            raise CommandError(_("You must provide either --company-id or --cnpj."))

        qs = Company.objects.all()
        if company_id:
            qs = qs.filter(id=company_id)
        if cnpj:
            digits = "".join(ch for ch in str(cnpj) if ch.isdigit())
            qs = qs.filter(cnpj=digits)

        try:
            company = qs.get()
        except Company.DoesNotExist:
            raise CommandError(_("Company not found with the given identifier."))
        except Company.MultipleObjectsReturned:
            raise CommandError(_("Multiple companies matched. Please specify a unique identifier."))

        now = timezone.now()
        within_cooldown = False
        if company.last_nsu_updated_at and (now - company.last_nsu_updated_at) < timedelta(minutes=settings.SEFAZ_COOLDOWN_MINUTES):
            within_cooldown = True

        if within_cooldown and not force:
            minutes_left = settings.SEFAZ_COOLDOWN_MINUTES - int((now - company.last_nsu_updated_at).total_seconds() // 60)
            self.stdout.write(self.style.WARNING(
                _("Blocked by SEFAZ cooldown. Try again in ~%(minutes)d minute(s) or use --force.")
                % {"minutes": max(0, minutes_left)}
            ))
            return

        # Perform the reset
        company.last_nsu = 0
        company.last_nsu_updated_at = now
        company.save(update_fields=["last_nsu", "last_nsu_updated_at", "updated_at"])

        if within_cooldown and force:
            self.stdout.write(self.style.WARNING(
                _("NSU reset forced within cooldown window for '%(name)s' (CNPJ %(cnpj)s). Proceed with caution.")
                % {"name": company.name, "cnpj": company.cnpj}
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                _("NSU reset successfully for '%(name)s' (CNPJ %(cnpj)s).")
                % {"name": company.name, "cnpj": company.cnpj}
            ))

        self.stdout.write(
            _(
                "Reminder: After resetting NSU, wait at least %(minutes)d minutes before running DF-e import to avoid cStat=656."
            ) % {"minutes": settings.SEFAZ_COOLDOWN_MINUTES}
        )
