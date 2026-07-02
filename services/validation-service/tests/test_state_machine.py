"""Tests de la machine d'état."""
import pytest
from app.state import MeasurementStateMachine, NormalState, CriticalState


class TestStateMachine:
    """Tests de la machine d'état."""

    def test_initial_state_normal(self):
        """L'état initial est NORMAL."""
        sm = MeasurementStateMachine()
        assert sm.is_normal()
        assert not sm.is_critical()
        assert isinstance(sm.get_state(), NormalState)

    def test_add_error_transitions_to_critical(self):
        """Ajouter une erreur fait transitionner vers CRITICAL."""
        sm = MeasurementStateMachine()
        sm.add_error("Test error")
        assert sm.is_critical()
        assert not sm.is_normal()
        assert len(sm.get_errors()) == 1

    def test_add_multiple_errors(self):
        """Ajouter plusieurs erreurs."""
        sm = MeasurementStateMachine()
        sm.add_errors(["Error 1", "Error 2"])
        assert sm.is_critical()
        assert len(sm.get_errors()) == 2

    def test_add_warning_does_not_change_state(self):
        """Un avertissement seul ne change pas l'état."""
        sm = MeasurementStateMachine()
        sm.add_warning("Test warning")
        assert sm.is_normal()
        assert len(sm.get_warnings()) == 1

    def test_error_and_warning(self):
        """État CRITICAL si erreur, même avec avertissements."""
        sm = MeasurementStateMachine()
        sm.add_warning("Warning")
        sm.add_error("Error")
        assert sm.is_critical()
        assert len(sm.get_warnings()) == 1
        assert len(sm.get_errors()) == 1

    def test_reset(self):
        """Reset remet l'état à NORMAL."""
        sm = MeasurementStateMachine()
        sm.add_error("Error")
        assert sm.is_critical()
        sm.reset()
        assert sm.is_normal()
        assert len(sm.get_errors()) == 0


class TestNormalState:
    """Tests de l'état NORMAL."""

    def test_normal_state_properties(self):
        """L'état NORMAL a les bonnes propriétés."""
        state = NormalState()
        assert state.name() == "NORMAL"
        assert state.is_valid() is True
        assert state.should_publish() is True


class TestCriticalState:
    """Tests de l'état CRITICAL."""

    def test_critical_state_properties(self):
        """L'état CRITICAL a les bonnes propriétés."""
        state = CriticalState()
        assert state.name() == "CRITICAL"
        assert state.is_valid() is False
        assert state.should_publish() is False