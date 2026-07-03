# Référence — MeasurementValidator

Documentation technique générée automatiquement depuis le code source via
[mkdocstrings](https://mkdocstrings.github.io/).

::: app.validator.MeasurementValidator
    options:
      show_source: true
      show_root_heading: true
      merge_init_into_class: true
      docstring_style: google

## Exemples d'usage (testés via `pytest --doctest-glob`)

### Mesure conforme → NORMAL

```python
>>> from app.models import RawMeasurement
>>> from app.validator import MeasurementValidator
>>> m = RawMeasurement(
...     type="pollution", city="paris", pollutant="no2",
...     value=45.0, latitude=48.8566, longitude=2.3522,
... )
>>> result = MeasurementValidator.validate(m, sensor_id="capteur_42")
>>> result.state
'NORMAL'
>>> result.valid
True
>>> result.aberrant
False

```

### Mesure incomplète → CRITICAL, non aberrante

Des champs requis manquants (ici `latitude`, `longitude`, `value`) rendent la
mesure impossible à interpréter. C'est une erreur **structurelle**, pas une
anomalie de capteur : `aberrant` reste `False`.

```python
>>> m = RawMeasurement(
...     type="pollution", city="paris", pollutant="no2",
...     value=None, latitude=None, longitude=None,
... )
>>> result = MeasurementValidator.validate(m, sensor_id="capteur_42")
>>> result.state
'CRITICAL'
>>> result.aberrant
False
>>> sorted(result.errors)
['latitude is required', 'longitude is required', 'value is required for pollution']

```

### Mesure aberrante → CRITICAL, `aberrant=True`

Une valeur présente mais physiquement implausible (ici NO2 = 10000 µg/m³,
très au-dessus du seuil absolu `POLLUTION_VALUE_MAX`) est elle aussi
CRITICAL, mais avec `aberrant=True` : c'est ce flag que `ingestion-service`
utilise pour faire transitionner l'état du capteur correspondant.

```python
>>> m = RawMeasurement(
...     type="pollution", city="paris", pollutant="no2",
...     value=10000.0, latitude=48.8566, longitude=2.3522,
... )
>>> result = MeasurementValidator.validate(m, sensor_id="capteur_42")
>>> result.state
'CRITICAL'
>>> result.aberrant
True
>>> result.errors
['value out of range: 10000.0']

```
