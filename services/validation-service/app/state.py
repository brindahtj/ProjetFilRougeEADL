from abc import ABC, abstractmethod

import logging

log = logging.getLogger("state_machine")


class MeasurementState(ABC):
    """Interface abstraite pour un état de mesure."""

    @abstractmethod
    def name(self) -> str:
        """Retourne le nom de l'état."""
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """Indique si la mesure est valide dans cet état."""
        pass

    @abstractmethod
    def should_publish(self) -> bool:
        """Indique si la mesure doit être publiée."""
        pass


class NormalState(MeasurementState):
    """État NORMAL : donnée complète et conforme."""

    def name(self) -> str:
        return "NORMAL"

    def is_valid(self) -> bool:
        return True

    def should_publish(self) -> bool:
        return True


class CriticalState(MeasurementState):
    """État CRITICAL : donnée incomplète ou aberrante."""

    def name(self) -> str:
        return "CRITICAL"

    def is_valid(self) -> bool:
        return False

    def should_publish(self) -> bool:
        return False


class MeasurementStateMachine:
    """
    Machine d'état pour une mesure.

    Encapsule la logique de transition entre NORMAL et CRITICAL.
    """

    def __init__(self):
        self._state: MeasurementState = NormalState()
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def reset(self) -> None:
        """Réinitialise l'état et les listes d'erreurs/avertissements."""
        self._state = NormalState()
        self._errors = []
        self._warnings = []

    def add_error(self, error: str) -> None:
        """Ajoute une erreur et met à jour l'état vers CRITICAL."""
        self._errors.append(error)
        self._transition_to_critical()

    def add_errors(self, errors: list[str]) -> None:
        """Ajoute plusieurs erreurs."""
        self._errors.extend(errors)
        if errors:
            self._transition_to_critical()

    def add_warning(self, warning: str) -> None:
        """Ajoute un avertissement (ne change pas l'état)."""
        self._warnings.append(warning)

    def add_warnings(self, warnings: list[str]) -> None:
        """Ajoute plusieurs avertissements."""
        self._warnings.extend(warnings)

    def _transition_to_critical(self) -> None:
        """Transition vers l'état CRITICAL."""
        if not isinstance(self._state, CriticalState):
            self._state = CriticalState()
            log.debug("Transition → CRITICAL")

    def get_state(self) -> MeasurementState:
        """Retourne l'état actuel."""
        return self._state

    def get_errors(self) -> list[str]:
        """Retourne la liste des erreurs."""
        return self._errors

    def get_warnings(self) -> list[str]:
        """Retourne la liste des avertissements."""
        return self._warnings

    def is_normal(self) -> bool:
        """Vérifie si l'état est NORMAL."""
        return isinstance(self._state, NormalState)

    def is_critical(self) -> bool:
        """Vérifie si l'état est CRITICAL."""
        return isinstance(self._state, CriticalState)
