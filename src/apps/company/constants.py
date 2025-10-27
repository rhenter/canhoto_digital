from django.utils.translation import gettext_lazy as _

UF_CHOICES = (
    ("AC", "AC"), ("AL", "AL"), ("AP", "AP"), ("AM", "AM"), ("BA", "BA"), ("CE", "CE"),
    ("DF", "DF"), ("ES", "ES"), ("GO", "GO"), ("MA", "MA"), ("MT", "MT"), ("MS", "MS"),
    ("MG", "MG"), ("PA", "PA"), ("PB", "PB"), ("PR", "PR"), ("PE", "PE"), ("PI", "PI"),
    ("RJ", "RJ"), ("RN", "RN"), ("RS", "RS"), ("RO", "RO"), ("RR", "RR"), ("SC", "SC"),
    ("SP", "SP"), ("SE", "SE"), ("TO", "TO"),
)
SEFAZ_ENV_CHOICES = (
    ("production", _("Production")),
    ("homologation", _("Homologation")),
)
