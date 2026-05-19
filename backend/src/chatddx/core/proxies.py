from chatddx.core.models import IdentityModel


class Identity(IdentityModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Identity"
        verbose_name_plural = "Identities"

    def __str__(self):
        return self.name
